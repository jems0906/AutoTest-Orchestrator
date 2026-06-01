from __future__ import annotations

import json
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import RetestFlag, Scenario, TestCase, TestResult, TestRun

FAILURE_BUCKETS = [
    "perception",
    "planning",
    "controls",
    "timing",
    "environment",
]


def execute_test_run(
    db: Session,
    run_type: str,
    triggered_by: str,
    only_risky: bool = False,
) -> dict:
    settings = get_settings()

    run = TestRun(run_type=run_type, status="running", triggered_by=triggered_by)
    db.add(run)
    db.flush()

    test_cases = db.scalars(select(TestCase).where(TestCase.active.is_(True))).all()
    if only_risky:
        test_cases = [tc for tc in test_cases if tc.scenario.risk_score >= 0.7]

    passed = 0
    failed = 0
    failures = Counter()

    for test_case in test_cases:
        result = _simulate_case(run.id, test_case)
        db.add(result)
        if result.outcome == "pass":
            passed += 1
        else:
            failed += 1
            failures[result.failure_category or "unknown"] += 1
            if test_case.scenario.risk_score >= 0.7:
                db.add(
                    RetestFlag(
                        scenario_id=test_case.scenario_id,
                        reason="High-risk scenario failed in latest run",
                    )
                )

    total = passed + failed
    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "failure_categories": dict(failures),
    }
    db.commit()

    _write_report(settings.report_dir, run.id, run.summary)
    return {"run_id": run.id, **run.summary}


def _simulate_case(run_id: int, test_case: TestCase) -> TestResult:
    scenario: Scenario = test_case.scenario
    failure_probability = max(0.05, scenario.risk_score * 0.6)
    outcome = "fail" if random.random() < failure_probability else "pass"

    failure_category = random.choice(FAILURE_BUCKETS) if outcome == "fail" else None
    duration = round(random.uniform(6.0, 90.0), 2)
    metrics = {
        "max_lateral_error_m": round(random.uniform(0.02, 0.7), 3),
        "intervention_count": 1 if outcome == "fail" else 0,
        "min_ttc_s": round(random.uniform(0.5, 5.0), 2),
        "duration_s": duration,
    }

    log_text = (
        f"[{datetime.now(UTC).isoformat()}] "
        f"TestCase={test_case.name} Scenario={scenario.name} Outcome={outcome.upper()}"
    )

    return TestResult(
        run_id=run_id,
        test_case_id=test_case.id,
        scenario_id=test_case.scenario_id,
        outcome=outcome,
        log_text=log_text,
        failure_category=failure_category,
        duration_sec=duration,
        metrics=metrics,
    )


def _write_report(report_dir: str, run_id: int, summary: dict) -> None:
    target_dir = Path(report_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / f"run_{run_id}.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
