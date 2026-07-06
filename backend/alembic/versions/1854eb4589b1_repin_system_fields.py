"""repin system fields

Built-in fields are now permanently pinned (FR-17); re-pin any that were
unpinned before this rule existed so they return to the card header.

Revision ID: 1854eb4589b1
Revises: c0beb8a32616
Create Date: 2026-07-05 23:08:20.633287

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1854eb4589b1'
down_revision: str | None = 'c0beb8a32616'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE fields SET is_pinned = 1 WHERE is_system = 1")


def downgrade() -> None:
    pass  # data fix only; nothing to restore
