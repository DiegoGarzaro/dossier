"""Person model — the aggregate root of a Dossier record."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.tag import person_tags

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.field import PersonField
    from app.models.tag import Tag


class Person(Base, TimestampMixin):
    """A family member record rendered as an ID-card (FR-6/7)."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), default=None)
    is_favorite: Mapped[bool] = mapped_column(default=False)

    fields: Mapped[list["PersonField"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PersonField.position",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Document.uploaded_at",
    )
    # Deliberately no cascade="delete-orphan" across the secondary: deleting
    # a person must delete the *assignment* (FK ON DELETE CASCADE on
    # person_tags), never the tag itself.
    tags: Mapped[list["Tag"]] = relationship(
        secondary=person_tags, back_populates="people", order_by="Tag.name"
    )
