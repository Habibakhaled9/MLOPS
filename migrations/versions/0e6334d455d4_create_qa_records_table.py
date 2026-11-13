"""create qa records table

Revision ID: 0e6334d455d4
Revises: 
Create Date: 2026-11-11 20:09:48.333675

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0e6334d455d4'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the qa_records table."""

    op.create_table(
        "qa_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("normalized_question", sa.Text(), nullable=False),
        sa.Column(
            "question_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "model_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "question_hash",
            "model_name",
            name="uq_qa_records_question_hash_model",
        ),
    )

    op.create_index(
        "ix_qa_records_created_at",
        "qa_records",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the qa_records table."""

    op.drop_index(
        "ix_qa_records_created_at",
        table_name="qa_records",
    )
    op.drop_table("qa_records")