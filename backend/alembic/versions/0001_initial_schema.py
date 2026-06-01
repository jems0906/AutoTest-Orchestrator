"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-01 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirements_id"), "requirements", ["id"], unique=False)
    op.create_index(op.f("ix_requirements_key"), "requirements", ["key"], unique=True)

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scenario_type", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("generated_from", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scenarios_id"), "scenarios", ["id"], unique=False)
    op.create_index(op.f("ix_scenarios_name"), "scenarios", ["name"], unique=False)
    op.create_index(op.f("ix_scenarios_scenario_type"), "scenarios", ["scenario_type"], unique=False)

    op.create_table(
        "execution_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_label", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_queue_id"), "execution_queue", ["id"], unique=False)
    op.create_index(op.f("ix_execution_queue_run_label"), "execution_queue", ["run_label"], unique=False)

    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("triggered_by", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_runs_id"), "test_runs", ["id"], unique=False)

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_cases_id"), "test_cases", ["id"], unique=False)
    op.create_index(op.f("ix_test_cases_name"), "test_cases", ["name"], unique=False)
    op.create_index(op.f("ix_test_cases_requirement_id"), "test_cases", ["requirement_id"], unique=False)
    op.create_index(op.f("ix_test_cases_scenario_id"), "test_cases", ["scenario_id"], unique=False)

    op.create_table(
        "retest_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retest_flags_id"), "retest_flags", ["id"], unique=False)
    op.create_index(op.f("ix_retest_flags_scenario_id"), "retest_flags", ["scenario_id"], unique=False)

    op.create_table(
        "test_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("log_text", sa.Text(), nullable=False),
        sa.Column("failure_category", sa.String(length=64), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_results_created_at"), "test_results", ["created_at"], unique=False)
    op.create_index(op.f("ix_test_results_id"), "test_results", ["id"], unique=False)
    op.create_index(op.f("ix_test_results_outcome"), "test_results", ["outcome"], unique=False)
    op.create_index(op.f("ix_test_results_run_id"), "test_results", ["run_id"], unique=False)
    op.create_index(op.f("ix_test_results_scenario_id"), "test_results", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_test_results_test_case_id"), "test_results", ["test_case_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_test_results_test_case_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_scenario_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_run_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_outcome"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_id"), table_name="test_results")
    op.drop_index(op.f("ix_test_results_created_at"), table_name="test_results")
    op.drop_table("test_results")

    op.drop_index(op.f("ix_retest_flags_scenario_id"), table_name="retest_flags")
    op.drop_index(op.f("ix_retest_flags_id"), table_name="retest_flags")
    op.drop_table("retest_flags")

    op.drop_index(op.f("ix_test_cases_scenario_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_requirement_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_name"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_id"), table_name="test_cases")
    op.drop_table("test_cases")

    op.drop_index(op.f("ix_test_runs_id"), table_name="test_runs")
    op.drop_table("test_runs")

    op.drop_index(op.f("ix_execution_queue_run_label"), table_name="execution_queue")
    op.drop_index(op.f("ix_execution_queue_id"), table_name="execution_queue")
    op.drop_table("execution_queue")

    op.drop_index(op.f("ix_scenarios_scenario_type"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_name"), table_name="scenarios")
    op.drop_index(op.f("ix_scenarios_id"), table_name="scenarios")
    op.drop_table("scenarios")

    op.drop_index(op.f("ix_requirements_key"), table_name="requirements")
    op.drop_index(op.f("ix_requirements_id"), table_name="requirements")
    op.drop_table("requirements")
