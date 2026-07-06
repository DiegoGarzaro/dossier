"""Person schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentOut
from app.schemas.field import FieldOut
from app.schemas.relationship import RelationshipOut


class PersonCreate(BaseModel):
    """Create a person (FR-6)."""

    full_name: str = Field(min_length=1, max_length=255)


class PersonUpdate(BaseModel):
    """Edit a person's name (FR-8)."""

    full_name: str = Field(min_length=1, max_length=255)


class PersonSummary(BaseModel):
    """Grid/list entry on the people index (FR-10)."""

    id: int
    full_name: str
    has_photo: bool
    updated_at: datetime
    pinned_fields: list[FieldOut]


class PersonDetail(BaseModel):
    """Full ID-card payload: person + fields + documents + relationships (FR-7)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    has_photo: bool = False
    fields: list[FieldOut]
    documents: list[DocumentOut]
    relationships: list[RelationshipOut] = []
    created_at: datetime
    updated_at: datetime
