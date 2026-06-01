from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RequirementCreate(BaseModel):
    key: str
    title: str
    description: str
    severity: str = "medium"


class RequirementRead(RequirementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ScenarioCreate(BaseModel):
    name: str
    scenario_type: str
    risk_score: float = 0.2
    parameters: dict[str, Any] = Field(default_factory=dict)
    generated_from: str | None = None


class ScenarioRead(ScenarioCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TestCaseCreate(BaseModel):
    name: str
    description: str
    requirement_id: int
    scenario_id: int
    priority: str = "medium"


class TestCaseRead(TestCaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    created_at: datetime


class TestRunRequest(BaseModel):
    run_type: str = "manual"
    triggered_by: str = "engineer"
    only_risky: bool = False


class TestRunSummary(BaseModel):
    run_id: int
    total: int
    passed: int
    failed: int
    pass_rate: float


class DashboardResponse(BaseModel):
    requirement_coverage: dict[str, Any]
    regression_trends: list[dict[str, Any]]
    failure_categories: list[dict[str, Any]]
    test_completeness: dict[str, Any]
    scenario_diversity: list[dict[str, Any]]
    coverage_gaps: list[dict[str, Any]]
    risk_flags: list[dict[str, Any]]
