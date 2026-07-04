"""Async data access for custom fields."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PersonField


class FieldRepository:
    """Repository for PersonField rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def get(self, field_id: int) -> PersonField | None:
        """Fetch a field by id.

        Args:
            field_id (int): The field id.

        Returns:
            PersonField | None: The field, or None if not found.
        """
        return await self._session.get(PersonField, field_id)

    async def next_position(self, person_id: int) -> int:
        """Compute the next sort position for a person's fields.

        Args:
            person_id (int): The owning person id.

        Returns:
            int: One past the current maximum position (0 when empty).
        """
        result = await self._session.execute(
            select(func.max(PersonField.position)).where(PersonField.person_id == person_id)
        )
        current_max = result.scalar_one_or_none()
        return 0 if current_max is None else current_max + 1

    async def list_for_person(self, person_id: int) -> list[PersonField]:
        """List a person's fields ordered by position.

        Args:
            person_id (int): The owning person id.

        Returns:
            list[PersonField]: The ordered fields.
        """
        result = await self._session.execute(
            select(PersonField)
            .where(PersonField.person_id == person_id)
            .order_by(PersonField.position)
        )
        return list(result.scalars().all())

    async def add(self, field: PersonField) -> PersonField:
        """Persist a new field.

        Args:
            field (PersonField): The field to add.

        Returns:
            PersonField: The persisted field with its id populated.
        """
        self._session.add(field)
        await self._session.flush()
        return field

    async def delete(self, field: PersonField) -> None:
        """Delete a field (FR-15).

        Args:
            field (PersonField): The field to delete.

        Returns:
            None
        """
        await self._session.delete(field)
        await self._session.flush()
