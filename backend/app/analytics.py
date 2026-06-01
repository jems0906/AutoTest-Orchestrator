from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from .models import Requirement, RetestFlag, Scenario, TestCase, TestResult


def build_dashboard_snapshot(db: Session) -> dict:
    return {
        "requirement_coverage": requirement_coverage(db),
        "regression_trends": regression_trends(db),
        "failure_categories": failure_categories(db),
        "test_completeness": test_completeness(db),
        "scenario_diversity": scenario_diversity(db),
        "coverage_gaps": coverage_gaps(db),
        "risk_flags": risk_flags(db),
    }


def requirement_coverage(db: Session) -> dict:
    total_requirements = db.scalar(select(func.count(Requirement.id))) or 0

    mapped_requirements = db.scalar(
        select(func.count(func.distinct(TestCase.requirement_id))).where(TestCase.active.is_(True))
    ) or 0

    passed_requirements = db.scalar(
        select(func.count(func.distinct(TestCase.requirement_id)))
        .join(TestResult, TestResult.test_case_id == TestCase.id)
        .where(TestResult.outcome == "pass")
    ) or 0

    mapped_pct = round((mapped_requirements / total_requirements) * 100, 2) if total_requirements else 0.0
    passed_pct = round((passed_requirements / total_requirements) * 100, 2) if total_requirements else 0.0

    return {
        "total_requirements": total_requirements,
        "mapped_requirements": mapped_requirements,
        "passed_requirements": passed_requirements,
        "mapped_coverage_pct": mapped_pct,
        "passed_coverage_pct": passed_pct,
    }


def regression_trends(db: Session, days: int = 14) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    day_bucket = (
        func.date(TestResult.created_at)
        if dialect_name == "sqlite"
        else func.date_trunc("day", TestResult.created_at)
    )

    rows = db.execute(
        select(
            day_bucket.label("day"),
            func.count(TestResult.id).label("total"),
            func.sum(case((TestResult.outcome == "pass", 1), else_=0)).label("passed"),
        )
        .where(TestResult.created_at >= since)
        .group_by("day")
        .order_by("day")
    ).all()

    result = []
    for row in rows:
        total = int(row.total or 0)
        passed = int(row.passed or 0)
        pass_rate = round((passed / total) * 100, 2) if total else 0.0
        day_value = row.day.strftime("%Y-%m-%d") if hasattr(row.day, "strftime") else str(row.day)
        result.append(
            {
                "day": day_value,
                "total": total,
                "passed": passed,
                "pass_rate": pass_rate,
            }
        )

    return result


def failure_categories(db: Session) -> list[dict]:
    rows = db.execute(
        select(TestResult.failure_category, func.count(TestResult.id).label("count"))
        .where(and_(TestResult.outcome == "fail", TestResult.failure_category.is_not(None)))
        .group_by(TestResult.failure_category)
        .order_by(func.count(TestResult.id).desc())
    ).all()

    return [{"category": row.failure_category, "count": int(row.count)} for row in rows]


def test_completeness(db: Session) -> dict:
    total_tests = db.scalar(select(func.count(TestCase.id)).where(TestCase.active.is_(True))) or 0

    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    executed_recently = db.scalar(
        select(func.count(func.distinct(TestResult.test_case_id))).where(
            TestResult.created_at >= seven_days_ago
        )
    ) or 0

    pct = round((executed_recently / total_tests) * 100, 2) if total_tests else 0.0
    return {
        "active_tests": total_tests,
        "executed_last_7_days": executed_recently,
        "completeness_pct": pct,
    }


def scenario_diversity(db: Session) -> list[dict]:
    rows = db.execute(
        select(Scenario.scenario_type, func.count(Scenario.id).label("count"))
        .group_by(Scenario.scenario_type)
        .order_by(func.count(Scenario.id).desc())
    ).all()
    return [{"scenario_type": row.scenario_type, "count": int(row.count)} for row in rows]


def coverage_gaps(db: Session) -> list[dict]:
    reqs = db.scalars(select(Requirement)).all()

    by_req = defaultdict(int)
    for req_id in db.scalars(select(TestCase.requirement_id).where(TestCase.active.is_(True))).all():
        by_req[req_id] += 1

    gaps = []
    for req in reqs:
        mapped = by_req.get(req.id, 0)
        if mapped == 0:
            gaps.append(
                {
                    "requirement_key": req.key,
                    "requirement_title": req.title,
                    "gap": "No tests mapped",
                }
            )
    return gaps


def risk_flags(db: Session) -> list[dict]:
    flags = db.scalars(
        select(RetestFlag).where(RetestFlag.status == "open").order_by(RetestFlag.created_at.desc())
    ).all()

    scenario_map = {
        scenario.id: scenario
        for scenario in db.scalars(select(Scenario).where(Scenario.id.in_([flag.scenario_id for flag in flags]))).all()
    } if flags else {}

    response = []
    for flag in flags:
        scenario = scenario_map.get(flag.scenario_id)
        response.append(
            {
                "flag_id": flag.id,
                "scenario": scenario.name if scenario else f"scenario-{flag.scenario_id}",
                "scenario_type": scenario.scenario_type if scenario else "unknown",
                "risk_score": scenario.risk_score if scenario else None,
                "reason": flag.reason,
                "created_at": flag.created_at.isoformat(),
            }
        )
    return response
