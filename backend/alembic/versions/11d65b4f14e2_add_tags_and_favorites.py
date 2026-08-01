"""add tags and favorites

Revision ID: 11d65b4f14e2
Revises: 4c0b49a25546
Create Date: 2026-08-01 00:02:55.342943

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '11d65b4f14e2'
down_revision: str | None = '4c0b49a25546'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'person_tags',
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'tag_id'),
    )
    with op.batch_alter_table('people', schema=None) as batch_op:
        # server_default backfills existing rows so NOT NULL doesn't fail on
        # an in-place upgrade (same lesson as c0beb8a32616 / is_system).
        batch_op.add_column(
            sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    with op.batch_alter_table('people', schema=None) as batch_op:
        batch_op.drop_column('is_favorite')

    op.drop_table('person_tags')
    op.drop_table('tags')
