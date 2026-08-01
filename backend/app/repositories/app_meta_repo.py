"""Async data access for the generic app_meta key/value store (G-36)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppMeta
from app.models.base import utcnow


class AppMetaRepository:
    """Repository for AppMeta rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def get(self, key: str) -> str | None:
        """Fetch a stored value by key.

        Args:
            key (str): The metadata key.

        Returns:
            str | None: The stored value, or None if the key was never set.
        """
        row = await self._session.get(AppMeta, key)
        return row.value if row is not None else None

    async def set(self, key: str, value: str) -> None:
        """Create or overwrite a stored value.

        Args:
            key (str): The metadata key.
            value (str): The value to store.

        Returns:
            None
        """
        row = await self._session.get(AppMeta, key)
        if row is None:
            self._session.add(AppMeta(key=key, value=value))
        else:
            row.value = value
            row.updated_at = utcnow()
        await self._session.flush()
