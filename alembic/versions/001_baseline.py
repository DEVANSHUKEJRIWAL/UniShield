"""Baseline schema — Week 3–5 tables.

Revision ID: 001_baseline
"""

from alembic import op
import sqlalchemy as sa

revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Week 3+ tables if not present (idempotent with init_db)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "agent_run_logs" not in existing:
        op.create_table(
            "agent_run_logs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_name", sa.String(64), nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("task_id", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("input_data", sa.JSON(), nullable=False),
            sa.Column("output", sa.Text(), nullable=True),
            sa.Column("tool_calls", sa.JSON(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_agent_run_logs_agent_name", "agent_run_logs", ["agent_name"])
        op.create_index("ix_agent_run_logs_tenant_id", "agent_run_logs", ["tenant_id"])

    if "cve_records" not in existing:
        op.create_table(
            "cve_records",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("cve_id", sa.String(32), nullable=False),
            sa.Column("cvss_score", sa.Float(), nullable=False),
            sa.Column("severity", sa.String(16), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("published", sa.String(32), nullable=True),
            sa.Column("raw", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cve_id"),
        )
        op.create_index("ix_cve_records_cve_id", "cve_records", ["cve_id"])

    if "insider_baselines" not in existing:
        op.create_table(
            "insider_baselines",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("user_id", sa.String(128), nullable=False),
            sa.Column("peer_group", sa.String(64), nullable=False),
            sa.Column("baseline", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_insider_baselines_tenant_id", "insider_baselines", ["tenant_id"])
        op.create_index("ix_insider_baselines_user_id", "insider_baselines", ["user_id"])


def downgrade() -> None:
    op.drop_table("insider_baselines")
    op.drop_table("cve_records")
    op.drop_table("agent_run_logs")
