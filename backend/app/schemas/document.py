"""Document metadata schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    """Document metadata shown in the documents section (FR-D5)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class DocumentUpdate(BaseModel):
    """Rename a document (FR-D2)."""

    title: str = Field(min_length=1, max_length=255)
