"""Relationship schemas (Epic E, Phase 2)."""

from pydantic import BaseModel, Field

from app.core.enums import RelationshipRole, RelationshipType


class RelationshipCreate(BaseModel):
    """Create a relationship as seen from `person_id`'s perspective (FR-22).

    `type` describes what `related_person_id` is *to* `person_id` — e.g.
    `type="parent"` means "the related person is my parent". `related_role`
    optionally genders the related person's side of the link (e.g.
    `type="parent", related_role="mother"` means "she is my mother") and
    must refine the given type (G-31).
    """

    person_id: int
    related_person_id: int
    type: RelationshipType
    related_role: RelationshipRole | None = None
    custom_label: str | None = Field(default=None, max_length=255)


class RelationshipOut(BaseModel):
    """A relationship resolved for display on one person's card (FR-23)."""

    id: int
    person_id: int
    person_name: str
    person_has_photo: bool
    label: str


class TreeNode(BaseModel):
    """One person in the relationship tree, placed by generation (Phase 2b).

    `generation` is relative to the center person: negative values are older
    generations (parents and godparents at -1), positive are younger
    (children at +1); all other links keep both people in the same
    generation. `kinship` is the derived relationship to the center person
    ("Mother", "Uncle", "Sister-in-law", …) or None when the connection has
    no common name (G-31).
    """

    id: int
    full_name: str
    generation: int
    kinship: str | None = None


class TreeEdge(BaseModel):
    """One link in the relationship tree (Phase 2b).

    For `parent` edges, `source_id` is always the parent side (the stored
    canonical direction); symmetric types keep their stored order.
    """

    source_id: int
    target_id: int
    type: RelationshipType
    label: str | None = None


class TreeOut(BaseModel):
    """A person's connected relationship graph, ready to render (Phase 2b)."""

    center_id: int
    nodes: list[TreeNode]
    edges: list[TreeEdge]
