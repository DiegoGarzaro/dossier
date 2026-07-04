"""Async data access for users."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    """Repository for User rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def count(self) -> int:
        """Count existing users (drives first-run detection, FR-5).

        Returns:
            int: Number of user rows.
        """
        result = await self._session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a user by username.

        Args:
            username (str): The username to look up.

        Returns:
            User | None: The user, or None if not found.
        """
        result = await self._session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        """Persist a new user.

        Args:
            user (User): The user to add.

        Returns:
            User: The persisted user with its id populated.
        """
        self._session.add(user)
        await self._session.flush()
        return user
