"""Async data access for people."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import FieldType
from app.models import Person, PersonField
from app.models.tag import person_tags


class PeopleRepository:
    """Repository for Person rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def list_with_details(self) -> list[Person]:
        """List every person with fields, documents, and tags eagerly loaded (FR-30).

        Used by the whole-dataset JSON export, which needs the full record for
        each person rather than the index-grid subset.

        Note: defined before `list()` because, once that method is bound in the
        class namespace, `list[...]` annotations below it resolve to the method
        instead of the builtin.

        Returns:
            list[Person]: All people ordered by name, fully loaded.
        """
        result = await self._session.execute(
            select(Person)
            .options(
                selectinload(Person.fields),
                selectinload(Person.documents),
                selectinload(Person.tags),
            )
            .order_by(Person.full_name)
        )
        return list(result.scalars().all())

    async def list(
        self,
        query: str | None = None,
        include_fields: bool = False,
        tag_ids: list[int] | None = None,
        favorites_only: bool = False,
    ) -> list[Person]:
        """List people, optionally filtered by name, field value, tag, or favorite status.

        Args:
            query (str | None): Case-insensitive substring to match. `%`/`_`
                are treated literally (escaped), so a query is a plain substring.
            include_fields (bool): When True, also match against custom field
                values. `sensitive`-type values are always excluded from the
                search so secrets stay unindexed (SEC-7).
            tag_ids (list[int] | None): When given, only people wearing at
                least one of these tags are returned (OR semantics).
            favorites_only (bool): When True, only favorited people are returned.

        Returns:
            list[Person]: People with favorites first, then ordered by name,
                with fields and tags eagerly loaded.
        """
        stmt = (
            select(Person)
            .options(selectinload(Person.fields), selectinload(Person.tags))
            .order_by(Person.is_favorite.desc(), Person.full_name)
        )
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            name_match = Person.full_name.ilike(pattern, escape="\\")
            if include_fields:
                # Correlated EXISTS over non-sensitive field values only (SEC-7).
                field_match = (
                    select(PersonField.id)
                    .where(
                        PersonField.person_id == Person.id,
                        PersonField.type != FieldType.sensitive,
                        PersonField.value.ilike(pattern, escape="\\"),
                    )
                    .exists()
                )
                stmt = stmt.where(or_(name_match, field_match))
            else:
                stmt = stmt.where(name_match)
        if favorites_only:
            stmt = stmt.where(Person.is_favorite.is_(True))
        if tag_ids:
            # Correlated EXISTS over the association table (OR semantics):
            # matches the style of the field-value EXISTS block above.
            tag_match = (
                select(person_tags.c.person_id)
                .where(
                    person_tags.c.person_id == Person.id,
                    person_tags.c.tag_id.in_(tag_ids),
                )
                .exists()
            )
            stmt = stmt.where(tag_match)
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

    async def get_by_name(self, full_name: str) -> Person | None:
        """Fetch a person by their exact name (used to de-duplicate imports).

        Args:
            full_name (str): The exact name to match.

        Returns:
            Person | None: The first person with that name, or None.
        """
        result = await self._session.execute(
            select(Person).where(Person.full_name == full_name).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_with_details(self, person_id: int) -> Person | None:
        """Fetch a person with fields, documents, and tags eagerly loaded (FR-7).

        Args:
            person_id (int): The person id.

        Returns:
            Person | None: The fully loaded person, or None.
        """
        result = await self._session.execute(
            select(Person)
            .options(
                selectinload(Person.fields),
                selectinload(Person.documents),
                selectinload(Person.tags),
            )
            .where(Person.id == person_id)
        )
        return result.scalar_one_or_none()

    async def get_with_tags(self, person_id: int) -> Person | None:
        """Fetch a person with their tags eagerly loaded, for assigning/unassigning.

        Args:
            person_id (int): The person id.

        Returns:
            Person | None: The person with tags loaded, or None.
        """
        result = await self._session.execute(
            select(Person).options(selectinload(Person.tags)).where(Person.id == person_id)
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
