"""allow legacy users without password hash

Revision ID: e33ed5d94362
Revises: 74a3fa63fe0a
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e33ed5d94362"
down_revision: Union[str, Sequence[str], None] = "74a3fa63fe0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow existing users to have no password hash."""
    op.alter_column(
        "users",
        "password_hash",
        nullable=True,
    )


def downgrade() -> None:
    """Restore the password hash column to NOT NULL."""
    op.alter_column(
        "users",
        "password_hash",
        nullable=False,
    )
