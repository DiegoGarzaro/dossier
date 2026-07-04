"""Person model — the aggregate root of a Dossier record."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.field import PersonField


class Person(Base, TimestampMixin):
    """A family member record rendered as an ID-card (FR-6/7)."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), default=None)

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
