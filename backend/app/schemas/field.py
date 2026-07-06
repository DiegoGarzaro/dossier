"""Custom field schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FieldType


class FieldCreate(BaseModel):
    """Payload to add a field to a person (FR-11/12)."""

    label: str = Field(min_length=1, max_length=255)
    value: str | None = Field(default=None, max_length=10_000)
    type: FieldType = FieldType.text
    is_pinned: bool = False


class FieldUpdate(BaseModel):
    """Partial update of a field (FR-15/16)."""

    label: str | None = Field(default=None, min_length=1, max_length=255)
    value: str | None = Field(default=None, max_length=10_000)
    type: FieldType | None = None
    is_pinned: bool | None = None


class FieldOut(BaseModel):
    """A field as rendered on the ID-card."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    value: str | None
    type: FieldType
    is_pinned: bool
    is_system: bool
    position: int
    updated_at: datetime


class FieldPosition(BaseModel):
    """One (field, position) pair in a reorder request."""

    id: int
    position: int


class ReorderRequest(BaseModel):
    """Bulk reorder of a person's fields (FR-15)."""

    items: list[FieldPosition]
