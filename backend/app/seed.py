from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Requirement, Scenario, TestCase
from .scenario_generator import generate_scenarios


def seed_data(db: Session) -> None:
    if db.scalar(select(Requirement.id).limit(1)):
        return

    reqs = [
        Requirement(
            key="REQ-PER-001",
            title="Detect pedestrians in crossing zones",
            description="Vehicle must detect and yield to pedestrians at marked and unmarked crossings.",
            severity="critical",
        ),
        Requirement(
            key="REQ-MRG-002",
            title="Safe lane merge behavior",
            description="Vehicle should complete merges while maintaining safe following distance.",
            severity="high",
        ),
        Requirement(
            key="REQ-INT-003",
            title="Signalized intersection compliance",
            description="Vehicle should comply with traffic light states and right-of-way rules.",
            severity="critical",
        ),
        Requirement(
            key="REQ-ROB-004",
            title="Robust handling of degraded sensors",
            description="System must safely operate under temporary sensor degradation.",
            severity="high",
        ),
    ]
    db.add_all(reqs)
    db.flush()

    generated = (
        generate_scenarios("pedestrian_crossing", 4, seed=1)
        + generate_scenarios("lane_merge", 4, seed=2)
        + generate_scenarios("intersection", 4, seed=3)
        + generate_scenarios("edge_case", 4, seed=4)
    )

    scenarios = [Scenario(**item) for item in generated]
    db.add_all(scenarios)
    db.flush()

    test_cases = []
    req_cycle = [reqs[0], reqs[1], reqs[2], reqs[3]]
    for idx, scenario in enumerate(scenarios, start=1):
        mapped_req = req_cycle[(idx - 1) % len(req_cycle)]
        test_cases.append(
            TestCase(
                name=f"TC-{scenario.scenario_type.upper()}-{idx:03d}",
                description=f"Validate {scenario.scenario_type} behavior under generated variation.",
                requirement_id=mapped_req.id,
                scenario_id=scenario.id,
                priority="high" if scenario.risk_score >= 0.7 else "medium",
            )
        )

    db.add_all(test_cases)
    db.commit()
