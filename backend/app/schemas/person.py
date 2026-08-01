"""Person schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentOut
from app.schemas.field import FieldOut
from app.schemas.relationship import RelationshipOut
from app.schemas.tag import TagOut


class PersonCreate(BaseModel):
    """Create a person (FR-6)."""

    full_name: str = Field(min_length=1, max_length=255)


class PersonUpdate(BaseModel):
    """Partially edit a person: name and/or favorite flag (FR-8, "Organizing people").

    Both fields are optional so a favorite toggle can be sent on its own
    without accidentally blanking the name — the service applies only the
    fields actually present in the request (`model_dump(exclude_unset=True)`).
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_favorite: bool | None = None


class PersonSummary(BaseModel):
    """Grid/list entry on the people index (FR-10)."""

    id: int
    full_name: str
    has_photo: bool
    updated_at: datetime
    is_favorite: bool
    tags: list[TagOut] = []
    pinned_fields: list[FieldOut]
    # Non-sensitive fields whose value matched a field-value search (FR-27),
    # shown on the card so the user sees why the person appeared. Empty when
    # not searching fields or when the match came only from the name.
    matched_fields: list[FieldOut] = []


class PersonDetail(BaseModel):
    """Full ID-card payload: person + fields + documents + relationships (FR-7)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    has_photo: bool = False
    is_favorite: bool = False
    tags: list[TagOut] = []
    fields: list[FieldOut]
    documents: list[DocumentOut]
    relationships: list[RelationshipOut] = []
    created_at: datetime
    updated_at: datetime
