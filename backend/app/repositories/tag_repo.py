"""Async data access for tags."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tag
from app.models.tag import person_tags


class TagRepository:
    """Repository for Tag rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def list_with_counts(self) -> list[tuple[Tag, int]]:
        """List every tag with how many people currently wear it.

        Returns:
            list[tuple[Tag, int]]: (tag, person_count) pairs ordered by name.
        """
        stmt = (
            select(Tag, func.count(person_tags.c.person_id))
            .outerjoin(person_tags, person_tags.c.tag_id == Tag.id)
            .group_by(Tag.id)
            .order_by(Tag.name)
        )
        result = await self._session.execute(stmt)
        return [(tag, count) for tag, count in result.all()]

    async def count_people(self, tag_id: int) -> int:
        """Count how many people currently wear a tag.

        Args:
            tag_id (int): The tag id.

        Returns:
            int: The number of people with this tag attached.
        """
        result = await self._session.execute(
            select(func.count(person_tags.c.person_id)).where(person_tags.c.tag_id == tag_id)
        )
        return result.scalar_one()

    async def get(self, tag_id: int) -> Tag | None:
        """Fetch a tag by id.

        Args:
            tag_id (int): The tag id.

        Returns:
            Tag | None: The tag, or None if not found.
        """
        return await self._session.get(Tag, tag_id)

    async def get_by_name(self, name: str) -> Tag | None:
        """Fetch a tag by name, matched case-insensitively.

        Args:
            name (str): The name to match (assumed already normalized).

        Returns:
            Tag | None: The matching tag, or None.
        """
        result = await self._session.execute(
            select(Tag).where(func.lower(Tag.name) == name.lower())
        )
        return result.scalar_one_or_none()

    async def add(self, tag: Tag) -> Tag:
        """Persist a new tag.

        Args:
            tag (Tag): The tag to add.

        Returns:
            Tag: The persisted tag with its id populated.
        """
        self._session.add(tag)
        await self._session.flush()
        return tag

    async def delete(self, tag: Tag) -> None:
        """Delete a tag; assignments disappear with it, people do not.

        Args:
            tag (Tag): The tag to delete.

        Returns:
            None
        """
        await self._session.delete(tag)
        await self._session.flush()
