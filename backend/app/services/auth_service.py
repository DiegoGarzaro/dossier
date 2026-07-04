"""Authentication business logic: first-run setup, login, logout, password change."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import AuthenticationError, ConflictError, RateLimitedError
from app.models import AuthSession, User
from app.models.base import utcnow
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository
from app.security import hash_password, new_token, verify_password


class AuthService:
    """Orchestrates account and session operations (Epic A)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)

    async def is_initialized(self) -> bool:
        """Report whether the initial admin account exists (FR-5).

        Returns:
            bool: True if at least one user exists.
        """
        return await self._users.count() > 0

    async def setup(self, username: str, password: str) -> User:
        """Create the initial admin account on first run (FR-5).

        Args:
            username (str): The admin username.
            password (str): The admin password (hashed before storage).

        Returns:
            User: The created admin user.

        Raises:
            ConflictError: If setup has already been completed.
        """
        if await self.is_initialized():
            raise ConflictError("Setup has already been completed")
        user = User(username=username, password_hash=hash_password(password))
        return await self._users.add(user)

    async def login(self, username: str, password: str) -> AuthSession:
        """Verify credentials and create a server-side session.

        Args:
            username (str): The username.
            password (str): The plaintext password.

        Returns:
            AuthSession: The new session whose id goes into the cookie.

        Raises:
            AuthenticationError: If the credentials are invalid.
            RateLimitedError: If the account is locked from repeated failures (G-07).
        """
        user = await self._users.get_by_username(username)
        if user is not None and user.locked_until is not None and user.locked_until > utcnow():
            raise RateLimitedError("Too many failed login attempts. Try again later.")
        if user is None or not verify_password(user.password_hash, password):
            if user is not None:
                await self._register_failed_attempt(user)
            raise AuthenticationError("Invalid username or password")
        user.failed_login_attempts = 0
        user.locked_until = None
        expires = utcnow() + timedelta(days=get_settings().session_idle_days)
        return await self._sessions.add(
            AuthSession(id=new_token(), user_id=user.id, expires_at=expires)
        )

    async def _register_failed_attempt(self, user: User) -> None:
        """Count a failed login and lock the account past the configured threshold.

        Commits immediately: the caller raises AuthenticationError right after this
        returns, and the request-scoped session rolls back on error, which would
        otherwise erase the failed attempt it's meant to record (G-07).

        Args:
            user (User): The user whose login just failed.

        Returns:
            None
        """
        settings = get_settings()
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(minutes=settings.login_lockout_minutes)
        await self._session.commit()

    async def logout(self, token: str) -> None:
        """Invalidate a session (FR-4).

        Args:
            token (str): The session token to delete.

        Returns:
            None
        """
        await self._sessions.delete(token)

    async def change_password(
        self, user: User, current_password: str, new_password: str, current_token: str
    ) -> None:
        """Change the password and revoke every other session (FR-3).

        Args:
            user (User): The authenticated user.
            current_password (str): The existing password, verified first.
            new_password (str): The replacement password.
            current_token (str): The active session token, kept alive.

        Returns:
            None

        Raises:
            AuthenticationError: If the current password is wrong.
        """
        if not verify_password(user.password_hash, current_password):
            raise AuthenticationError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self._sessions.delete_for_user(user.id, keep_token=current_token)
