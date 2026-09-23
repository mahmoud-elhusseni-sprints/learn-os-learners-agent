"""persist visual artifacts with assistant messages

Revision ID: 9b7c1f2e4a10
Revises: 74a3fa63fe0a
Create Date: 2026-09-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9b7c1f2e4a10"
down_revision: Union[str, Sequence[str], None] = "74a3fa63fe0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("artifacts", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "artifacts")
