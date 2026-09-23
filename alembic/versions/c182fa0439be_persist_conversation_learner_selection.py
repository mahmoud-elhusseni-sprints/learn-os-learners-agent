"""Persist explicit learner selection per conversation.

Revision ID: c182fa0439be
Revises: 74a3fa63fe0a
"""

import sqlalchemy as sa

from alembic import op

revision = "c182fa0439be"
down_revision = "74a3fa63fe0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Existing conversations have no selection until one is supplied."""
    op.add_column(
        "conversation_sessions",
        sa.Column("learner_name_or_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Remove selection storage without removing messages."""
    op.drop_column("conversation_sessions", "learner_name_or_id")
