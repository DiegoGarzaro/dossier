"""Tag business logic: normalization, dedup, and person assignment ("Organizing people")."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Tag
from app.repositories.people_repo import PeopleRepository
from app.repositories.tag_repo import TagRepository
from app.schemas.tag import TagCreate, TagOut, TagUpdate


def normalize_name(name: str) -> str:
    """Collapse a tag name to single spaces and trim its edges.

    Args:
        name (str): The raw name as submitted.

    Returns:
        str: The normalized name, e.g. `"  Close   Family "` -> `"Close Family"`.
    """
    return " ".join(name.split())


class TagService:
    """Orchestrates tag CRUD and person assignment."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session
        self._tags = TagRepository(session)
        self._people = PeopleRepository(session)

    async def list(self) -> list[TagOut]:
        """List every tag with how many people currently wear it.

        Returns:
            list[TagOut]: Tags ordered by name, each with its person count.
        """
        return [
            TagOut(id=tag.id, name=tag.name, person_count=count)
            for tag, count in await self._tags.list_with_counts()
        ]

    async def create(self, data: TagCreate) -> TagOut:
        """Create a tag, rejecting a case-insensitive duplicate name.

        Args:
            data (TagCreate): The requested name.

        Returns:
            TagOut: The created tag (person_count is always 0: it's brand new).

        Raises:
            ConflictError: A tag with the same name (any case) already exists.
        """
        name = normalize_name(data.name)
        if await self._tags.get_by_name(name) is not None:
            raise ConflictError("A tag with this name already exists")
        tag = await self._tags.add(Tag(name=name))
        return TagOut(id=tag.id, name=tag.name, person_count=0)

    async def rename(self, tag_id: int, data: TagUpdate) -> TagOut:
        """Rename a tag, applying the same normalization and duplicate rule as create.

        Args:
            tag_id (int): The tag id.
            data (TagUpdate): The new name.

        Returns:
            TagOut: The renamed tag with its current person count.

        Raises:
            NotFoundError: If the tag does not exist.
            ConflictError: Another tag already has this name (any case).
        """
        tag = await self._tags.get(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found")
        name = normalize_name(data.name)
        duplicate = await self._tags.get_by_name(name)
        if duplicate is not None and duplicate.id != tag.id:
            raise ConflictError("A tag with this name already exists")
        tag.name = name
        count = await self._tags.count_people(tag.id)
        return TagOut(id=tag.id, name=tag.name, person_count=count)

    async def delete(self, tag_id: int) -> None:
        """Delete a tag; its assignments disappear with it, the people do not.

        Args:
            tag_id (int): The tag id.

        Returns:
            None

        Raises:
            NotFoundError: If the tag does not exist.
        """
        tag = await self._tags.get(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found")
        await self._tags.delete(tag)

    async def assign(self, person_id: int, name: str) -> TagOut:
        """Attach a tag to a person, creating it first if it's new.

        Idempotent: assigning an already-attached tag (matched case-insensitively
        after normalization) succeeds without creating a duplicate assignment.

        Args:
            person_id (int): The person id.
            name (str): The tag name to find-or-create and attach.

        Returns:
            TagOut: The (possibly newly created) tag now attached to the
                person, with its current person count.

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people.get_with_tags(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        normalized = normalize_name(name)
        tag = await self._tags.get_by_name(normalized)
        if tag is None:
            tag = await self._tags.add(Tag(name=normalized))
        if tag not in person.tags:
            person.tags.append(tag)
        await self._session.flush()  # make the new assignment visible to the count query below
        count = await self._tags.count_people(tag.id)
        return TagOut(id=tag.id, name=tag.name, person_count=count)

    async def unassign(self, person_id: int, tag_id: int) -> None:
        """Detach a tag from a person, leaving both the tag and the person intact.

        Args:
            person_id (int): The person id.
            tag_id (int): The tag id.

        Returns:
            None

        Raises:
            NotFoundError: If the person or the tag does not exist.
        """
        person = await self._people.get_with_tags(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        tag = await self._tags.get(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found")
        if tag in person.tags:
            person.tags.remove(tag)
