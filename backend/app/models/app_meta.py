"""Generic key/value store for small pieces of app-wide state (G-36).

Kept intentionally generic (rather than a one-off `last_backup_at` column
somewhere) so the next bit of singleton app state doesn't need its own
migration.
"""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class AppMeta(Base):
    """A single key/value row of miscellaneous application state."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
