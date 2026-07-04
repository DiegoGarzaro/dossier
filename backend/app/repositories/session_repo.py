"""Async data access for server-side sessions."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthSession
from app.models.base import utcnow


class SessionRepository:
    """Repository for AuthSession rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def get_valid(self, token: str) -> AuthSession | None:
        """Fetch a non-expired session with its user eagerly loaded.

        Args:
            token (str): The session token from the cookie.

        Returns:
            AuthSession | None: The valid session, or None.
        """
        result = await self._session.execute(
            select(AuthSession).where(AuthSession.id == token, AuthSession.expires_at > utcnow())
        )
        return result.scalar_one_or_none()

    async def add(self, auth_session: AuthSession) -> AuthSession:
        """Persist a new session.

        Args:
            auth_session (AuthSession): The session to add.

        Returns:
            AuthSession: The persisted session.
        """
        self._session.add(auth_session)
        await self._session.flush()
        return auth_session

    async def delete(self, token: str) -> None:
        """Delete a session by token (logout, FR-4).

        Args:
            token (str): The session token to invalidate.

        Returns:
            None
        """
        await self._session.execute(delete(AuthSession).where(AuthSession.id == token))

    async def delete_for_user(self, user_id: int, keep_token: str | None = None) -> None:
        """Delete all of a user's sessions, optionally keeping the current one.

        Args:
            user_id (int): The owning user id.
            keep_token (str | None): A session token to preserve, if any.

        Returns:
            None
        """
        stmt = delete(AuthSession).where(AuthSession.user_id == user_id)
        if keep_token is not None:
            stmt = stmt.where(AuthSession.id != keep_token)
        await self._session.execute(stmt)

    async def purge_expired(self) -> int:
        """Delete all sessions whose expiry has passed (G-10).

        Returns:
            int: The number of rows deleted.
        """
        result = await self._session.execute(
            delete(AuthSession).where(AuthSession.expires_at <= utcnow())
        )
        return result.rowcount
