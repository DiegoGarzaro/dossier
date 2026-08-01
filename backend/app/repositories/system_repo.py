"""Async data access for vault-wide summary counts (G-36).

Kept as its own repository (rather than scattering `count()` methods across
five per-aggregate repositories) since a summary spanning every table is a
cross-cutting query, not something owned by a single aggregate.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models import Document, Person, PersonField, Relationship, Tag


class SystemRepository:
    """Read-only row counts across every user-data table."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def counts(self) -> dict[str, int]:
        """Count every row in each user-data table.

        Returns:
            dict[str, int]: Counts keyed by "people", "fields", "documents",
                "relationships", and "tags".
        """
        return {
            "people": await self._count(Person.id),
            "fields": await self._count(PersonField.id),
            "documents": await self._count(Document.id),
            "relationships": await self._count(Relationship.id),
            "tags": await self._count(Tag.id),
        }

    async def _count(self, column: InstrumentedAttribute) -> int:
        """Count the rows of one table via its primary key column.

        Args:
            column (InstrumentedAttribute): The primary key column to count.

        Returns:
            int: The row count.
        """
        result = await self._session.execute(select(func.count(column)))
        return result.scalar_one()
