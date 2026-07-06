"""Relationship business logic: canonicalize direction, resolve inverse labels (Epic E)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RelationshipType
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.models import Relationship
from app.repositories.people_repo import PeopleRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.relationship import RelationshipCreate, RelationshipOut

# Human label for each type, as seen by the person who *chose* it — e.g.
# selecting type="parent" means "the related person is my parent".
_LABELS: dict[RelationshipType, str] = {
    RelationshipType.spouse: "Spouse",
    RelationshipType.parent: "Parent",
    RelationshipType.child: "Child",
    RelationshipType.sibling: "Sibling",
}

# The stored type's label as seen from the *other* side of the link.
_INVERSE_TYPE: dict[RelationshipType, RelationshipType] = {
    RelationshipType.spouse: RelationshipType.spouse,
    RelationshipType.sibling: RelationshipType.sibling,
    RelationshipType.parent: RelationshipType.child,
}


class RelationshipService:
    """Orchestrates relationship links between people (Epic E, FR-22-25)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._relationships = RelationshipRepository(session)
        self._people = PeopleRepository(session)

    async def create(self, data: RelationshipCreate) -> RelationshipOut:
        """Link two people, canonicalizing direction and rejecting invalid links.

        `child` is never stored: linking "related_person is my child" is
        normalized to a `parent` row with the two people swapped, so a
        `parent`/`child` pair always has exactly one canonical row regardless
        of which side created it (FR-22/23, Architecture §4.2).

        Args:
            data (RelationshipCreate): The requester, target, type, and optional
                custom label.

        Returns:
            RelationshipOut: The new link, resolved for the requester's side.

        Raises:
            InvalidInputError: Self-link, or a custom type missing its label.
            NotFoundError: Either person does not exist.
            ConflictError: The same relationship already exists, in either
                stored order.
        """
        if data.person_id == data.related_person_id:
            raise InvalidInputError("A person can't be related to themselves")
        if data.type == RelationshipType.custom and not (data.custom_label or "").strip():
            raise InvalidInputError("Custom relationships need a label")
        person = await self._people.get(data.person_id)
        if person is None:
            raise NotFoundError("Person not found")
        related = await self._people.get(data.related_person_id)
        if related is None:
            raise NotFoundError("Related person not found")

        if data.type == RelationshipType.child:
            # "related_person is my child" -> I am the parent.
            person_a_id, person_b_id, stored_type = (
                data.person_id,
                data.related_person_id,
                RelationshipType.parent,
            )
        elif data.type == RelationshipType.parent:
            # "related_person is my parent" -> they are the parent.
            person_a_id, person_b_id, stored_type = (
                data.related_person_id,
                data.person_id,
                RelationshipType.parent,
            )
        else:
            person_a_id, person_b_id, stored_type = (
                data.person_id,
                data.related_person_id,
                data.type,
            )

        duplicate = await self._relationships.exists(person_a_id, person_b_id, stored_type)
        if not duplicate and stored_type != RelationshipType.parent:
            # parent/child direction is already canonical; only symmetric
            # types (spouse/sibling/custom) can be duplicated in reverse order.
            duplicate = await self._relationships.exists(person_b_id, person_a_id, stored_type)
        if duplicate:
            raise ConflictError("This relationship already exists")

        relationship = Relationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            type=stored_type,
            custom_label=data.custom_label if stored_type == RelationshipType.custom else None,
        )
        await self._relationships.add(relationship)

        label = data.custom_label if data.type == RelationshipType.custom else _LABELS[data.type]
        return RelationshipOut(
            id=relationship.id,
            person_id=related.id,
            person_name=related.full_name,
            person_has_photo=related.photo_path is not None,
            label=label,
        )

    async def remove(self, relationship_id: int) -> None:
        """Remove a relationship from either person's record (FR-25).

        Args:
            relationship_id (int): The relationship id.

        Returns:
            None

        Raises:
            NotFoundError: If the relationship does not exist.
        """
        relationship = await self._relationships.get(relationship_id)
        if relationship is None:
            raise NotFoundError("Relationship not found")
        await self._relationships.delete(relationship)

    async def list_for_person(self, person_id: int) -> list[RelationshipOut]:
        """Resolve a person's relationships with the correct inverse label (FR-23).

        Args:
            person_id (int): The viewing person's id.

        Returns:
            list[RelationshipOut]: The counterpart and resolved label for each
                link, grouped by label then counterpart name.
        """
        rows = await self._relationships.list_for_person(person_id)
        views = []
        for row in rows:
            viewer_is_a = row.person_a_id == person_id
            other = row.person_b if viewer_is_a else row.person_a
            if row.type == RelationshipType.custom:
                label = row.custom_label or "Custom"
            else:
                shown_type = _INVERSE_TYPE[row.type] if viewer_is_a else row.type
                label = _LABELS[shown_type]
            views.append(
                RelationshipOut(
                    id=row.id,
                    person_id=other.id,
                    person_name=other.full_name,
                    person_has_photo=other.photo_path is not None,
                    label=label,
                )
            )
        return sorted(views, key=lambda view: (view.label, view.person_name))
