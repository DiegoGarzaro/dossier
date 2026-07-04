"""Relationship link model (Epic E, Phase 2 — modeled now per Architecture.md §4)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import RelationshipType
from app.models.base import Base, utcnow


class Relationship(Base):
    """A directed link between two people; inverse label derived on read (FR-23)."""

    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint("person_a_id != person_b_id", name="ck_relationships_not_self"),
        UniqueConstraint("person_a_id", "person_b_id", "type", name="uq_relationships_pair_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_a_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    person_b_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    type: Mapped[RelationshipType] = mapped_column(String(20))
    custom_label: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
