"""At-a-glance vault summary schema (G-36)."""

from datetime import datetime

from pydantic import BaseModel


class SystemSummary(BaseModel):
    """Record counts, storage usage, and last-backup timestamp for Settings."""

    people: int
    fields: int
    documents: int
    relationships: int
    tags: int
    uploads_bytes: int
    database_bytes: int
    last_backup_at: datetime | None
