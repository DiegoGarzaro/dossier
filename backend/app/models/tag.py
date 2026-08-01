"""Tag model — user-defined labels for organizing people (Phase 2, "Organizing people")."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.person import Person

# Many-to-many assignment of tags to people. Both foreign keys cascade on
# delete so removing either side of the pair drops the *assignment* row —
# never the tag, and never the person (see Tag.people below).
person_tags = Table(
    "person_tags",
    Base.metadata,
    Column("person_id", ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """A user-defined label that can be attached to any number of people."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    # No cascade="delete-orphan": deleting a tag or a person must only ever
    # remove the association row (handled by the FKs above), never the tag
    # itself or the other people still wearing it.
    people: Mapped[list["Person"]] = relationship(
        secondary=person_tags, back_populates="tags", order_by="Person.full_name"
    )
