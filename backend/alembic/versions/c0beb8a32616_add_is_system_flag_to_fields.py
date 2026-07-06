"""add is_system flag to fields

Revision ID: c0beb8a32616
Revises: 24c5a13c0d6b
Create Date: 2026-07-05 22:53:13.261561

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c0beb8a32616'
down_revision: str | None = '24c5a13c0d6b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('fields', schema=None) as batch_op:
        # server_default backfills existing rows so NOT NULL doesn't fail on
        # an in-place upgrade (same lesson as the login-lockout migration).
        batch_op.add_column(
            sa.Column('is_system', sa.Boolean(), nullable=False, server_default='0')
        )
    # Mark pre-existing seeded fields (created before this flag existed) as
    # system fields, matched by their fixed seeded labels.
    op.execute(
        "UPDATE fields SET is_system = 1 "
        "WHERE label IN ('Document number', 'Address', 'Nationality')"
    )


def downgrade() -> None:
    with op.batch_alter_table('fields', schema=None) as batch_op:
        batch_op.drop_column('is_system')
