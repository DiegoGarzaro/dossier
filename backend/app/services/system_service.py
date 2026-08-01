"""At-a-glance vault summary: record counts, storage usage, last backup (G-36)."""

from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories.app_meta_repo import AppMetaRepository
from app.repositories.system_repo import SystemRepository
from app.schemas.system import SystemSummary
from app.services.backup_service import LAST_BACKUP_KEY


def _directory_size(path: Path) -> int:
    """Sum the size of every regular file under a directory tree.

    Args:
        path (Path): The directory to walk.

    Returns:
        int: Total bytes, or 0 if the directory doesn't exist yet.
    """
    if not path.is_dir():
        return 0
    return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())


def _file_size(path: Path) -> int:
    """Size of a single file.

    Args:
        path (Path): The file to size.

    Returns:
        int: The file's size in bytes, or 0 if it doesn't exist yet.
    """
    return path.stat().st_size if path.is_file() else 0


class SystemService:
    """Builds the vault-wide summary shown in Settings."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._system = SystemRepository(session)
        self._app_meta = AppMetaRepository(session)

    async def summary(self) -> SystemSummary:
        """Count every record type and report storage usage and the last backup time.

        Returns:
            SystemSummary: Counts for people/fields/documents/relationships/tags,
                bytes used by uploads and the database file, and
                `last_backup_at` (None until the first successful backup).
        """
        settings = get_settings()
        counts = await self._system.counts()
        last_backup = await self._app_meta.get(LAST_BACKUP_KEY)
        return SystemSummary(
            **counts,
            uploads_bytes=_directory_size(settings.uploads_dir),
            database_bytes=_file_size(settings.data_dir / "app.db"),
            last_backup_at=datetime.fromisoformat(last_backup) if last_backup else None,
        )
