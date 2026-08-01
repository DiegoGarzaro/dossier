"""seed date of birth system field

Revision ID: 4c0b49a25546
Revises: 598d3db2b20d
Create Date: 2026-07-31 19:11:24.809725

Data-only migration: "Date of birth" joined the seeded system fields (FR-17),
so people created before this change need the field backfilled. It is inserted
at position 1 (right after Document number) and everything from that position
onward shifts down by one, preserving the relative order of fields the user
already arranged.

"""
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4c0b49a25546'
down_revision: str | None = '598d3db2b20d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LABEL = 'Date of birth'
POSITION = 1

fields = sa.table(
    'fields',
    sa.column('id', sa.Integer),
    sa.column('person_id', sa.Integer),
    sa.column('label', sa.String),
    sa.column('value', sa.Text),
    sa.column('type', sa.String),
    sa.column('is_pinned', sa.Boolean),
    sa.column('is_system', sa.Boolean),
    sa.column('position', sa.Integer),
    sa.column('created_at', sa.DateTime),
    sa.column('updated_at', sa.DateTime),
)

people = sa.table('people', sa.column('id', sa.Integer))


def upgrade() -> None:
    bind = op.get_bind()
    already_have = set(
        bind.execute(sa.select(fields.c.person_id).where(fields.c.label == LABEL)).scalars()
    )
    missing = [
        person_id
        for person_id in bind.execute(sa.select(people.c.id)).scalars()
        if person_id not in already_have
    ]
    if not missing:
        return

    bind.execute(
        sa.update(fields)
        .where(fields.c.person_id.in_(missing), fields.c.position >= POSITION)
        .values(position=fields.c.position + 1)
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    bind.execute(
        sa.insert(fields),
        [
            {
                'person_id': person_id,
                'label': LABEL,
                'value': None,
                'type': 'date',
                'is_pinned': True,
                'is_system': True,
                'position': POSITION,
                'created_at': now,
                'updated_at': now,
            }
            for person_id in missing
        ],
    )


def downgrade() -> None:
    # Reverses the backfill; any date the user typed into the field is lost,
    # which is what rolling this revision back means.
    bind = op.get_bind()
    affected = list(
        bind.execute(
            sa.select(fields.c.person_id).where(
                fields.c.label == LABEL, fields.c.is_system.is_(True)
            )
        ).scalars()
    )
    if not affected:
        return
    bind.execute(sa.delete(fields).where(fields.c.label == LABEL, fields.c.is_system.is_(True)))
    bind.execute(
        sa.update(fields)
        .where(fields.c.person_id.in_(affected), fields.c.position > POSITION)
        .values(position=fields.c.position - 1)
    )
