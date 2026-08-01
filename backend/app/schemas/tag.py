"""Tag schemas (Phase 2, "Organizing people")."""

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """Create a tag."""

    name: str = Field(min_length=1, max_length=50)


class TagUpdate(BaseModel):
    """Rename a tag."""

    name: str = Field(min_length=1, max_length=50)


class TagOut(BaseModel):
    """A tag as rendered in the tag list or on a person's card."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    person_count: int = 0
