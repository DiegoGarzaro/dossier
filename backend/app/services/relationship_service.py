"""Relationship business logic: canonicalize direction, resolve inverse labels (Epic E)."""

from collections import deque

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RelationshipRole, RelationshipType
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.models import Relationship
from app.repositories.people_repo import PeopleRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.relationship import (
    RelationshipCreate,
    RelationshipOut,
    TreeEdge,
    TreeNode,
    TreeOut,
)
from app.services.kinship import gender_from_roles, kinship_term

# Human label for each type, as seen by the person who *chose* it — e.g.
# selecting type="parent" means "the related person is my parent".
_LABELS: dict[RelationshipType, str] = {
    RelationshipType.spouse: "Spouse",
    RelationshipType.partner: "Partner",
    RelationshipType.parent: "Parent",
    RelationshipType.child: "Child",
    RelationshipType.sibling: "Sibling",
    RelationshipType.friend: "Friend",
    RelationshipType.colleague: "Colleague",
    RelationshipType.godparent: "Godparent",
    RelationshipType.godchild: "Godchild",
}

# The stored type's label as seen from the *other* side of the link.
_INVERSE_TYPE: dict[RelationshipType, RelationshipType] = {
    RelationshipType.spouse: RelationshipType.spouse,
    RelationshipType.partner: RelationshipType.partner,
    RelationshipType.sibling: RelationshipType.sibling,
    RelationshipType.friend: RelationshipType.friend,
    RelationshipType.colleague: RelationshipType.colleague,
    RelationshipType.parent: RelationshipType.child,
    RelationshipType.godparent: RelationshipType.godchild,
}

# The structural type each role refines: picking the role implies the type.
_ROLE_TYPES: dict[RelationshipRole, RelationshipType] = {
    RelationshipRole.father: RelationshipType.parent,
    RelationshipRole.mother: RelationshipType.parent,
    RelationshipRole.son: RelationshipType.child,
    RelationshipRole.daughter: RelationshipType.child,
    RelationshipRole.brother: RelationshipType.sibling,
    RelationshipRole.sister: RelationshipType.sibling,
    RelationshipRole.husband: RelationshipType.spouse,
    RelationshipRole.wife: RelationshipType.spouse,
    RelationshipRole.godfather: RelationshipType.godparent,
    RelationshipRole.godmother: RelationshipType.godparent,
    RelationshipRole.godson: RelationshipType.godchild,
    RelationshipRole.goddaughter: RelationshipType.godchild,
}

# Types stored with the older side as person_a; their alias swaps the pair.
_CANONICAL_OF_ALIAS: dict[RelationshipType, RelationshipType] = {
    RelationshipType.child: RelationshipType.parent,
    RelationshipType.godchild: RelationshipType.godparent,
}
_DIRECTIONAL_TYPES = (RelationshipType.parent, RelationshipType.godparent)


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

        `child` and `godchild` are never stored: linking "related_person is
        my (god)child" is normalized to a `parent`/`godparent` row with the
        two people swapped, so each pair always has exactly one canonical row
        regardless of which side created it (FR-22/23, Architecture §4.2).
        An optional `related_role` (e.g. `mother`) genders the related
        person's side and becomes their label (G-31).

        Args:
            data (RelationshipCreate): The requester, target, type, and
                optional role / custom label.

        Returns:
            RelationshipOut: The new link, resolved for the requester's side.

        Raises:
            InvalidInputError: Self-link, a custom type missing its label, or
                a role that doesn't refine the given type.
            NotFoundError: Either person does not exist.
            ConflictError: The same relationship already exists, in either
                stored order.
        """
        if data.person_id == data.related_person_id:
            raise InvalidInputError("A person can't be related to themselves")
        if data.type == RelationshipType.custom and not (data.custom_label or "").strip():
            raise InvalidInputError("Custom relationships need a label")
        if data.related_role is not None and _ROLE_TYPES[data.related_role] != data.type:
            raise InvalidInputError("The role doesn't match the relationship type")
        person = await self._people.get(data.person_id)
        if person is None:
            raise NotFoundError("Person not found")
        related = await self._people.get(data.related_person_id)
        if related is None:
            raise NotFoundError("Related person not found")

        if data.type in _CANONICAL_OF_ALIAS:
            # "related_person is my (god)child" -> I am the (god)parent.
            person_a_id, person_b_id = data.person_id, data.related_person_id
            stored_type = _CANONICAL_OF_ALIAS[data.type]
        elif data.type in _DIRECTIONAL_TYPES:
            # "related_person is my (god)parent" -> they are the older side.
            person_a_id, person_b_id = data.related_person_id, data.person_id
            stored_type = data.type
        else:
            person_a_id, person_b_id = data.person_id, data.related_person_id
            stored_type = data.type

        duplicate = await self._relationships.exists(person_a_id, person_b_id, stored_type)
        if not duplicate and stored_type not in _DIRECTIONAL_TYPES:
            # Directional rows are already canonical; only symmetric types
            # can be duplicated in reverse order.
            duplicate = await self._relationships.exists(person_b_id, person_a_id, stored_type)
        if duplicate:
            raise ConflictError("This relationship already exists")

        # The role describes the related person; store it on whichever side
        # they landed after canonicalization.
        role = data.related_role.value if data.related_role else None
        relationship = Relationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            type=stored_type,
            custom_label=data.custom_label if stored_type == RelationshipType.custom else None,
            role_a=role if person_a_id == data.related_person_id else None,
            role_b=role if person_b_id == data.related_person_id else None,
        )
        await self._relationships.add(relationship)

        if role:
            label = role.capitalize()
        elif data.type == RelationshipType.custom:
            label = data.custom_label
        else:
            label = _LABELS[data.type]
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
            other_role = row.role_b if viewer_is_a else row.role_a
            if other_role:
                label = other_role.capitalize()
            elif row.type == RelationshipType.custom:
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

    # Traversal bounds for the tree view (Phase 2b): the whole connected
    # component, clamped so a pathological graph can't blow up the response.
    _MAX_TREE_NODES = 100
    _MAX_GENERATION_SPAN = 3

    async def tree(self, person_id: int) -> TreeOut:
        """Walk a person's connected relationship graph into a renderable shape.

        Generations are assigned in two waves so the chart is *structurally
        stable* — the same family reads identically no matter who is centered
        (G-32). Wave 1 walks only structural (blood/marriage) edges from the
        center: `parent` shifts one generation (older side up), spouse,
        partner, and sibling keep both people level. This lays a consistent
        generation ladder. Wave 2 then places anyone reachable only through a
        soft edge (godparent shifts a generation, friend/colleague/custom stay
        level), after which their own structural family is expanded again.
        Because blood edges always win, a grandparent who is *also* a
        godparent keeps their blood generation instead of being pulled up by
        the one-hop shortcut. On conflicting paths the first assignment wins.

        Each node also gets a derived `kinship` caption relative to the center
        ("Mother", "Uncle", "Sister-in-law", …) computed from its walk path,
        gendered by any roles recorded on the person's links (G-31).

        Args:
            person_id (int): The center person's id.

        Returns:
            TreeOut: Nodes with relative generations and kinship captions,
                plus the edges between included nodes.

        Raises:
            NotFoundError: If the center person does not exist.
        """
        center = await self._people.get(person_id)
        if center is None:
            raise NotFoundError("Person not found")

        rows = await self._relationships.list_all()
        # Per row: the kinship step walking a->b and b->a, and the generation
        # shift (directional rows are canonical: person_a is the older side).
        # Structural edges define the generation ladder; soft edges only place
        # people with no blood/marriage path, so they can't distort it.
        structural: dict[int, list[tuple[int, int, str]]] = {}
        soft: dict[int, list[tuple[int, int, str]]] = {}
        roles_by_person: dict[int, set[str]] = {}
        for row in rows:
            if row.type == RelationshipType.parent:
                bucket, shift, step_ab, step_ba = structural, 1, "down", "up"
            elif row.type == RelationshipType.sibling:
                bucket, shift, step_ab, step_ba = structural, 0, "sib", "sib"
            elif row.type in (RelationshipType.spouse, RelationshipType.partner):
                bucket, shift, step_ab, step_ba = structural, 0, str(row.type), str(row.type)
            elif row.type == RelationshipType.godparent:
                bucket, shift, step_ab, step_ba = soft, 1, "gdown", "gup"
            else:
                bucket, shift, step_ab, step_ba = soft, 0, str(row.type), str(row.type)
            bucket.setdefault(row.person_a_id, []).append((row.person_b_id, shift, step_ab))
            bucket.setdefault(row.person_b_id, []).append((row.person_a_id, -shift, step_ba))
            if row.role_a:
                roles_by_person.setdefault(row.person_a_id, set()).add(row.role_a)
            if row.role_b:
                roles_by_person.setdefault(row.person_b_id, set()).add(row.role_b)

        generations: dict[int, int] = {person_id: 0}
        paths: dict[int, tuple[str, ...]] = {person_id: ()}
        names: dict[int, str] = {person_id: center.full_name}

        def walk(source: int, adjacency: dict[int, list[tuple[int, int, str]]]) -> None:
            """BFS from `source` over one edge set, filling generations/paths."""
            queue = deque([source])
            while queue and len(generations) < self._MAX_TREE_NODES:
                current = queue.popleft()
                for other_id, shift, step in adjacency.get(current, []):
                    if other_id in generations:
                        continue
                    generation = generations[current] + shift
                    if abs(generation) > self._MAX_GENERATION_SPAN:
                        continue
                    generations[other_id] = generation
                    paths[other_id] = paths[current] + (step,)
                    queue.append(other_id)

        # Wave 1: exhaust the blood/marriage ladder. Waves alternate — each
        # soft-added person may open a new structural subtree, so re-run
        # structural expansion until a soft pass adds nobody new.
        walk(person_id, structural)
        while len(generations) < self._MAX_TREE_NODES:
            before = len(generations)
            for placed in list(generations):
                for other_id, shift, step in soft.get(placed, []):
                    if other_id in generations:
                        continue
                    generation = generations[placed] + shift
                    if abs(generation) > self._MAX_GENERATION_SPAN:
                        continue
                    generations[other_id] = generation
                    paths[other_id] = paths[placed] + (step,)
                    walk(other_id, structural)
            if len(generations) == before:
                break

        for row in rows:
            for side in (row.person_a, row.person_b):
                if side.id in generations and side.id not in names:
                    names[side.id] = side.full_name

        nodes = [
            TreeNode(
                id=node_id,
                full_name=names[node_id],
                generation=generation,
                kinship=kinship_term(
                    paths[node_id],
                    gender_from_roles(roles_by_person.get(node_id, ())),
                ),
            )
            for node_id, generation in generations.items()
        ]
        edges = [
            TreeEdge(
                source_id=row.person_a_id,
                target_id=row.person_b_id,
                type=row.type,
                label=row.custom_label,
            )
            for row in rows
            if row.person_a_id in generations and row.person_b_id in generations
        ]
        return TreeOut(
            center_id=person_id,
            nodes=sorted(nodes, key=lambda node: (node.generation, node.full_name)),
            edges=edges,
        )
