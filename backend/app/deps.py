"""FastAPI dependencies: session resolution and the auth guard (FR-1)."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import AuthSession, User
from app.models.base import utcnow
from app.repositories.session_repo import SessionRepository
from app.security import SESSION_COOKIE

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_auth(request: Request, db: DbSession) -> AuthSession | None:
    """Resolve the current session from the cookie, with sliding renewal (FR-4).

    Args:
        request (Request): The incoming request.
        db (AsyncSession): The request-scoped database session.

    Returns:
        AuthSession | None: The valid session, or None when unauthenticated.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    auth = await SessionRepository(db).get_valid(token)
    if auth is None:
        return None
    renewed = utcnow() + timedelta(days=get_settings().session_idle_days)
    if renewed - auth.expires_at > timedelta(hours=1):
        auth.expires_at = renewed
    return auth


CurrentAuth = Annotated[AuthSession | None, Depends(get_current_auth)]


async def get_current_user(auth: CurrentAuth) -> User:
    """Require an authenticated user; 401 otherwise (FR-1 / SEC-1).

    Args:
        auth (AuthSession | None): The resolved session, if any.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: 401 when no valid session exists.
    """
    if auth is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return auth.user


CurrentUser = Annotated[User, Depends(get_current_user)]
