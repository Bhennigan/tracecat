"""Add Base Camp OS tables

Revision ID: a1b2c3d4e5f8
Revises: 49a5c7464ab7, 7aab03def5b6, c2a4f8a5cf72
Create Date: 2026-02-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f8"
down_revision: tuple[str, ...] = ("49a5c7464ab7", "7aab03def5b6", "c2a4f8a5cf72")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enums
    ingestionstate_enum = postgresql.ENUM(
        "received",
        "analyzing",
        "validating",
        "transforming",
        "loading",
        "complete",
        "failed",
        name="ingestionstate",
        create_type=False,
    )
    ingestionstate_enum.create(op.get_bind(), checkfirst=True)

    datasourcetype_enum = postgresql.ENUM(
        "file_upload",
        "api",
        "file_watch",
        "tracecat_trigger",
        name="datasourcetype",
        create_type=False,
    )
    datasourcetype_enum.create(op.get_bind(), checkfirst=True)

    schemastatus_enum = postgresql.ENUM(
        "draft",
        "active",
        "deprecated",
        name="schemastatus",
        create_type=False,
    )
    schemastatus_enum.create(op.get_bind(), checkfirst=True)

    fileformat_enum = postgresql.ENUM(
        "json",
        "csv",
        "excel",
        name="fileformat",
        create_type=False,
    )
    fileformat_enum.create(op.get_bind(), checkfirst=True)

    # Create basecamp_schema table
    op.create_table(
        "basecamp_schema",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("surrogate_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), default=1, nullable=False),
        sa.Column(
            "status",
            schemastatus_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column("fields", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace.id"],
            ondelete="CASCADE",
            name="fk_basecamp_schema_workspace_id_workspace",
        ),
        sa.PrimaryKeyConstraint("surrogate_id", name="pk_basecamp_schema"),
        sa.UniqueConstraint(
            "workspace_id", "name", "version", name="uq_basecamp_schema_workspace_id_name_version"
        ),
    )
    op.create_index(
        "ix_basecamp_schema_id", "basecamp_schema", ["id"], unique=True
    )
    op.create_index(
        "ix_basecamp_schema_workspace_id", "basecamp_schema", ["workspace_id"]
    )

    # Create data_source table
    op.create_table(
        "data_source",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("surrogate_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", datasourcetype_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace.id"],
            ondelete="CASCADE",
            name="fk_data_source_workspace_id_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["schema_id"],
            ["basecamp_schema.id"],
            ondelete="SET NULL",
            name="fk_data_source_schema_id_basecamp_schema",
        ),
        sa.PrimaryKeyConstraint("surrogate_id", name="pk_data_source"),
        sa.UniqueConstraint(
            "workspace_id", "name", name="uq_data_source_workspace_id_name"
        ),
    )
    op.create_index("ix_data_source_id", "data_source", ["id"], unique=True)
    op.create_index("ix_data_source_workspace_id", "data_source", ["workspace_id"])

    # Create ingestion_job table
    op.create_table(
        "ingestion_job",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("surrogate_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "state",
            ingestionstate_enum,
            server_default="received",
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_format", fileformat_enum, nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=True),
        sa.Column("processed_records", sa.Integer(), default=0, nullable=False),
        sa.Column("failed_records", sa.Integer(), default=0, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace.id"],
            ondelete="CASCADE",
            name="fk_ingestion_job_workspace_id_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_source.id"],
            ondelete="SET NULL",
            name="fk_ingestion_job_source_id_data_source",
        ),
        sa.ForeignKeyConstraint(
            ["schema_id"],
            ["basecamp_schema.id"],
            ondelete="SET NULL",
            name="fk_ingestion_job_schema_id_basecamp_schema",
        ),
        sa.PrimaryKeyConstraint("surrogate_id", name="pk_ingestion_job"),
    )
    op.create_index("ix_ingestion_job_id", "ingestion_job", ["id"], unique=True)
    op.create_index("ix_ingestion_job_workspace_id", "ingestion_job", ["workspace_id"])
    op.create_index("ix_ingestion_job_state", "ingestion_job", ["state"])

    # Create data_record table
    op.create_table(
        "data_record",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("surrogate_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace.id"],
            ondelete="CASCADE",
            name="fk_data_record_workspace_id_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["schema_id"],
            ["basecamp_schema.id"],
            ondelete="CASCADE",
            name="fk_data_record_schema_id_basecamp_schema",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ingestion_job.id"],
            ondelete="SET NULL",
            name="fk_data_record_job_id_ingestion_job",
        ),
        sa.PrimaryKeyConstraint("surrogate_id", name="pk_data_record"),
    )
    op.create_index("ix_data_record_id", "data_record", ["id"], unique=True)
    op.create_index("ix_data_record_workspace_id", "data_record", ["workspace_id"])
    op.create_index("ix_data_record_schema_id", "data_record", ["schema_id"])
    op.create_index("ix_data_record_job_id", "data_record", ["job_id"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index("ix_data_record_job_id", table_name="data_record")
    op.drop_index("ix_data_record_schema_id", table_name="data_record")
    op.drop_index("ix_data_record_workspace_id", table_name="data_record")
    op.drop_index("ix_data_record_id", table_name="data_record")
    op.drop_table("data_record")

    op.drop_index("ix_ingestion_job_state", table_name="ingestion_job")
    op.drop_index("ix_ingestion_job_workspace_id", table_name="ingestion_job")
    op.drop_index("ix_ingestion_job_id", table_name="ingestion_job")
    op.drop_table("ingestion_job")

    op.drop_index("ix_data_source_workspace_id", table_name="data_source")
    op.drop_index("ix_data_source_id", table_name="data_source")
    op.drop_table("data_source")

    op.drop_index("ix_basecamp_schema_workspace_id", table_name="basecamp_schema")
    op.drop_index("ix_basecamp_schema_id", table_name="basecamp_schema")
    op.drop_table("basecamp_schema")

    # Drop enums
    sa.Enum(name="fileformat").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="schemastatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="datasourcetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ingestionstate").drop(op.get_bind(), checkfirst=True)
