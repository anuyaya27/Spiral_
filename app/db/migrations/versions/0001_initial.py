"""Initial schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "uploads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parsing_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_uploads_owner_id", "uploads", ["owner_id"], unique=False)
    op.create_index("ix_uploads_platform", "uploads", ["platform"], unique=False)
    op.create_index("ix_uploads_status", "uploads", ["status"], unique=False)
    op.create_index("ix_uploads_retention_until", "uploads", ["retention_until"], unique=False)

    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("upload_id", sa.String(length=36), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_participants_upload_id", "participants", ["upload_id"], unique=False)
    op.create_index("ix_participants_normalized_id", "participants", ["normalized_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("upload_id", sa.String(length=36), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender_id", sa.String(length=36), sa.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("encrypted_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_upload_id", "messages", ["upload_id"], unique=False)
    op.create_index("ix_messages_ts", "messages", ["ts"], unique=False)
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("upload_id", sa.String(length=36), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_upload_id", "jobs", ["upload_id"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_task_id", "jobs", ["task_id"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("upload_id", sa.String(length=36), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("mixed_signal_index", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_upload_id", "reports", ["upload_id"], unique=True)

    op.create_table(
        "excerpts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("upload_id", sa.String(length=36), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.String(length=36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("encrypted_excerpt", sa.Text(), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_excerpts_upload_id", "excerpts", ["upload_id"], unique=False)
    op.create_index("ix_excerpts_message_id", "excerpts", ["message_id"], unique=False)
    op.create_index("ix_excerpts_purpose", "excerpts", ["purpose"], unique=False)


def downgrade() -> None:
    op.drop_table("excerpts")
    op.drop_table("reports")
    op.drop_table("jobs")
    op.drop_table("messages")
    op.drop_table("participants")
    op.drop_table("uploads")
    op.drop_table("users")

