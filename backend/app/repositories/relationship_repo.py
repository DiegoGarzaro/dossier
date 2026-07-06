"""Async data access for relationships."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RelationshipType
from app.models import Relationship


class RelationshipRepository:
    """Repository for Relationship rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def list_for_person(self, person_id: int) -> list[Relationship]:
        """List relationships involving a person, with both sides' Person loaded.

        Args:
            person_id (int): The person id (either side of the stored link).

        Returns:
            list[Relationship]: Rows where the person is person_a or person_b.
        """
        stmt = select(Relationship).where(
            or_(Relationship.person_a_id == person_id, Relationship.person_b_id == person_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[Relationship]:
        """List every relationship with both sides' Person loaded (Phase 2b).

        The whole table is fetched in one query; the tree service walks the
        graph in memory, which stays cheap at family-vault scale.

        Returns:
            list[Relationship]: All relationship rows.
        """
        result = await self._session.execute(select(Relationship))
        return list(result.scalars().all())

    async def get(self, relationship_id: int) -> Relationship | None:
        """Fetch a relationship by id.

        Args:
            relationship_id (int): The relationship id.

        Returns:
            Relationship | None: The relationship, or None if not found.
        """
        return await self._session.get(Relationship, relationship_id)

    async def exists(self, person_a_id: int, person_b_id: int, type_: RelationshipType) -> bool:
        """Check whether an exact (ordered) relationship row already exists.

        Args:
            person_a_id (int): The person_a side to check.
            person_b_id (int): The person_b side to check.
            type_ (RelationshipType): The stored (canonical) type to check.

        Returns:
            bool: True if a matching row exists.
        """
        stmt = select(Relationship.id).where(
            Relationship.person_a_id == person_a_id,
            Relationship.person_b_id == person_b_id,
            Relationship.type == type_,
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def add(self, relationship: Relationship) -> Relationship:
        """Persist a new relationship.

        Args:
            relationship (Relationship): The relationship to add.

        Returns:
            Relationship: The persisted relationship with its id populated.
        """
        self._session.add(relationship)
        await self._session.flush()
        return relationship

    async def delete(self, relationship: Relationship) -> None:
        """Delete a relationship.

        Args:
            relationship (Relationship): The relationship to delete.

        Returns:
            None
        """
        await self._session.delete(relationship)
        await self._session.flush()
