"""Custom field model — the EAV store behind unlimited fields (FR-11/12)."""

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FieldType
from app.models.base import Base, TimestampMixin
from app.models.person import Person


class PersonField(Base, TimestampMixin):
    """A single label/value pair attached to a person."""

    __tablename__ = "fields"
    __table_args__ = (Index("ix_fields_person_position", "person_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(255))
    value: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[FieldType] = mapped_column(String(20), default=FieldType.text)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    # Seeded built-in fields (FR-17): value/pin editable, label/type/delete locked.
    is_system: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(default=0)

    person: Mapped[Person] = relationship(back_populates="fields")
