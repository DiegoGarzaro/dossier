"""Async data access for people."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Person


class PeopleRepository:
    """Repository for Person rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def list(self, query: str | None = None) -> list[Person]:
        """List people, optionally filtered by a name search (FR-10/26).

        Args:
            query (str | None): Case-insensitive substring to match against full_name.

        Returns:
            list[Person]: People ordered by name, with fields eagerly loaded.
        """
        stmt = select(Person).options(selectinload(Person.fields)).order_by(Person.full_name)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Person.full_name.ilike(f"%{escaped}%", escape="\\"))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, person_id: int) -> Person | None:
        """Fetch a person by id.

        Args:
            person_id (int): The person id.

        Returns:
            Person | None: The person, or None if not found.
        """
        return await self._session.get(Person, person_id)

    async def get_with_details(self, person_id: int) -> Person | None:
        """Fetch a person with fields and documents eagerly loaded (FR-7).

        Args:
            person_id (int): The person id.

        Returns:
            Person | None: The fully loaded person, or None.
        """
        result = await self._session.execute(
            select(Person)
            .options(selectinload(Person.fields), selectinload(Person.documents))
            .where(Person.id == person_id)
        )
        return result.scalar_one_or_none()

    async def add(self, person: Person) -> Person:
        """Persist a new person.

        Args:
            person (Person): The person to add.

        Returns:
            Person: The persisted person with its id populated.
        """
        self._session.add(person)
        await self._session.flush()
        return person

    async def delete(self, person: Person) -> None:
        """Delete a person; fields/documents/relationships cascade (FR-9).

        Args:
            person (Person): The person to delete.

        Returns:
            None
        """
        await self._session.delete(person)
        await self._session.flush()
