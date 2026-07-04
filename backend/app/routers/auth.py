"""Auth routes: status, first-run setup, login, logout, password change (Epic A)."""

from fastapi import APIRouter, Request, Response

from app.config import get_settings
from app.deps import CurrentAuth, CurrentUser, DbSession
from app.schemas.auth import AuthStatus, LoginRequest, PasswordChangeRequest, SetupRequest
from app.security import SESSION_COOKIE
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    """Attach the session cookie to a response.

    Args:
        response (Response): The response to mutate.
        request (Request): The request, used to decide the Secure flag.
        token (str): The session token.

    Returns:
        None
    """
    settings = get_settings()
    # trust_proxy: treat the connection as HTTPS when running behind a TLS-terminating proxy
    secure = settings.trust_proxy or request.url.scheme == "https"
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_idle_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@router.get("/status", response_model=AuthStatus)
async def status(auth: CurrentAuth, db: DbSession) -> AuthStatus:
    """Report first-run and authentication state; also seeds the CSRF cookie."""
    return AuthStatus(
        initialized=await AuthService(db).is_initialized(),
        authenticated=auth is not None,
        username=auth.user.username if auth else None,
    )


@router.post("/setup", response_model=AuthStatus)
async def setup(
    data: SetupRequest, request: Request, response: Response, db: DbSession
) -> AuthStatus:
    """Create the initial admin account and log in (FR-5)."""
    service = AuthService(db)
    await service.setup(data.username, data.password)
    session = await service.login(data.username, data.password)
    _set_session_cookie(response, request, session.id)
    return AuthStatus(initialized=True, authenticated=True, username=data.username)


@router.post("/login", response_model=AuthStatus)
async def login(
    data: LoginRequest, request: Request, response: Response, db: DbSession
) -> AuthStatus:
    """Verify credentials and start a session."""
    session = await AuthService(db).login(data.username, data.password)
    _set_session_cookie(response, request, session.id)
    return AuthStatus(initialized=True, authenticated=True, username=data.username)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: DbSession) -> None:
    """Invalidate the current session (FR-4)."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await AuthService(db).logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post("/password", status_code=204)
async def change_password(
    data: PasswordChangeRequest, request: Request, user: CurrentUser, db: DbSession
) -> None:
    """Change the password and revoke other sessions (FR-3)."""
    token = request.cookies.get(SESSION_COOKIE, "")
    await AuthService(db).change_password(user, data.current_password, data.new_password, token)
