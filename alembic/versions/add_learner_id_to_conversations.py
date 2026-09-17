"""add learner id to conversations

Revision ID: add_learner_id
Revises: 74a3fa63fe0a
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "add_learner_id"
down_revision: Union[str, Sequence[str], None] = "74a3fa63fe0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_sessions",
        sa.Column(
            "learner_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_conversation_sessions_learner_id",
        "conversation_sessions",
        ["learner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_sessions_learner_id",
        table_name="conversation_sessions",
    )

    op.drop_column(
        "conversation_sessions",
        "learner_id",
    )