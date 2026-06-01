from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .analytics import build_dashboard_snapshot
from .auth import Role, require_role
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .execution import execute_test_run
from .models import Requirement, Scenario, TestCase, TestResult, TestRun
from .scenario_generator import generate_scenarios
from .schemas import (
    DashboardResponse,
    RequirementCreate,
    RequirementRead,
    ScenarioRead,
    TestCaseCreate,
    TestCaseRead,
    TestRunRequest,
    TestRunSummary,
)
from .scheduler import RegressionScheduler
from .seed import seed_data

settings = get_settings()
scheduler = RegressionScheduler(timezone=settings.scheduler_timezone)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DBSession = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "timestamp": datetime.now(UTC).isoformat()}


@app.post(
    f"{settings.api_prefix}/requirements",
    response_model=RequirementRead,
    dependencies=[Depends(require_role(Role.engineer))],
)
def create_requirement(payload: RequirementCreate, db: DBSession):
    exists = db.scalar(select(Requirement).where(Requirement.key == payload.key))
    if exists:
        raise HTTPException(status_code=409, detail="Requirement key already exists")

    req = Requirement(**payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@app.get(
    f"{settings.api_prefix}/requirements",
    response_model=list[RequirementRead],
    dependencies=[Depends(require_role(Role.viewer))],
)
def list_requirements(db: DBSession):
    return db.scalars(select(Requirement).order_by(Requirement.created_at.desc())).all()


@app.post(
    f"{settings.api_prefix}/scenarios/generate",
    response_model=list[ScenarioRead],
    dependencies=[Depends(require_role(Role.engineer))],
)
def create_generated_scenarios(
    scenario_type: str,
    db: DBSession,
    count: int = 8,
    seed: int | None = None,
):
    generated = generate_scenarios(scenario_type=scenario_type, count=count, seed=seed, generated_from="api")
    scenarios = [Scenario(**item) for item in generated]
    db.add_all(scenarios)
    db.commit()
    for scenario in scenarios:
        db.refresh(scenario)
    return scenarios


@app.get(
    f"{settings.api_prefix}/scenarios",
    response_model=list[ScenarioRead],
    dependencies=[Depends(require_role(Role.viewer))],
)
def list_scenarios(db: DBSession):
    return db.scalars(select(Scenario).order_by(Scenario.created_at.desc())).all()


@app.post(
    f"{settings.api_prefix}/test-cases",
    response_model=TestCaseRead,
    dependencies=[Depends(require_role(Role.engineer))],
)
def create_test_case(payload: TestCaseCreate, db: DBSession):
    requirement = db.get(Requirement, payload.requirement_id)
    scenario = db.get(Scenario, payload.scenario_id)
    if not requirement or not scenario:
        raise HTTPException(status_code=400, detail="Invalid requirement_id or scenario_id")

    test_case = TestCase(**payload.model_dump())
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case


@app.get(
    f"{settings.api_prefix}/test-cases",
    response_model=list[TestCaseRead],
    dependencies=[Depends(require_role(Role.viewer))],
)
def list_test_cases(db: DBSession):
    return db.scalars(select(TestCase).order_by(TestCase.created_at.desc())).all()


@app.post(
    f"{settings.api_prefix}/runs/execute",
    response_model=TestRunSummary,
    dependencies=[Depends(require_role(Role.engineer))],
)
def run_tests(payload: TestRunRequest, db: DBSession):
    summary = execute_test_run(
        db=db,
        run_type=payload.run_type,
        triggered_by=payload.triggered_by,
        only_risky=payload.only_risky,
    )
    return TestRunSummary(**summary)


@app.get(f"{settings.api_prefix}/runs", dependencies=[Depends(require_role(Role.viewer))])
def list_runs(db: DBSession):
    runs = db.scalars(select(TestRun).order_by(TestRun.started_at.desc()).limit(30)).all()
    return [
        {
            "id": run.id,
            "run_type": run.run_type,
            "status": run.status,
            "triggered_by": run.triggered_by,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "summary": run.summary,
        }
        for run in runs
    ]


@app.get(f"{settings.api_prefix}/traceability", dependencies=[Depends(require_role(Role.viewer))])
def requirement_traceability(db: DBSession):
    requirements = db.scalars(select(Requirement).order_by(Requirement.key)).all()

    output = []
    for req in requirements:
        rows = db.execute(
            select(TestCase, Scenario)
            .join(Scenario, Scenario.id == TestCase.scenario_id)
            .where(TestCase.requirement_id == req.id)
        ).all()

        tests = []
        for test_case, scenario in rows:
            latest_result = db.scalar(
                select(TestResult)
                .where(TestResult.test_case_id == test_case.id)
                .order_by(TestResult.created_at.desc())
                .limit(1)
            )
            tests.append(
                {
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                    "scenario": scenario.name,
                    "scenario_type": scenario.scenario_type,
                    "last_outcome": latest_result.outcome if latest_result else "not-run",
                }
            )

        output.append(
            {
                "requirement_key": req.key,
                "requirement_title": req.title,
                "severity": req.severity,
                "test_count": len(tests),
                "tests": tests,
            }
        )

    return output


@app.get(
    f"{settings.api_prefix}/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_role(Role.viewer))],
)
def dashboard(db: DBSession):
    return build_dashboard_snapshot(db)


@app.post(
    f"{settings.api_prefix}/scheduler/run-nightly",
    dependencies=[Depends(require_role(Role.admin))],
)
def trigger_nightly_run():
    scheduler.queue_nightly_run()
    return {"message": "Nightly regression run queued and executed"}
