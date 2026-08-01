"""Relationship link model (Epic E, Phase 2 — modeled now per Architecture.md §4)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RelationshipType
from app.models.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.person import Person


class Relationship(Base):
    """A directed link between two people; inverse label derived on read (FR-23).

    `type` is always stored in its canonical direction: `child` is never
    persisted — creating one normalizes to a `parent` row with the two
    people swapped, so the (pair, type) unique constraint holds regardless
    of which person initiated the link (Architecture §4.2).
    """

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
    # Optional gendered role per side (RelationshipRole values, e.g. "mother"
    # on the parent side of a parent row) — G-31. Validated in the service.
    role_a: Mapped[str | None] = mapped_column(String(20), default=None)
    role_b: Mapped[str | None] = mapped_column(String(20), default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    person_a: Mapped["Person"] = relationship(foreign_keys=[person_a_id], lazy="joined")
    person_b: Mapped["Person"] = relationship(foreign_keys=[person_b_id], lazy="joined")
