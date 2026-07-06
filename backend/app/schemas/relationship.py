"""Relationship schemas (Epic E, Phase 2)."""

from pydantic import BaseModel, Field

from app.core.enums import RelationshipType


class RelationshipCreate(BaseModel):
    """Create a relationship as seen from `person_id`'s perspective (FR-22).

    `type` describes what `related_person_id` is *to* `person_id` — e.g.
    `type="parent"` means "the related person is my parent".
    """

    person_id: int
    related_person_id: int
    type: RelationshipType
    custom_label: str | None = Field(default=None, max_length=255)


class RelationshipOut(BaseModel):
    """A relationship resolved for display on one person's card (FR-23)."""

    id: int
    person_id: int
    person_name: str
    person_has_photo: bool
    label: str
