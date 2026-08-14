"""CSRF double-submit middleware and security response headers (SEC-3)."""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.security import CSRF_COOKIE, CSRF_HEADER, new_token

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF: a readable cookie must be echoed in a request header.

    The cookie is issued on the first response; the SPA reads it and sends it
    back as X-CSRF-Token on every state-changing request. SameSite=Lax cookies
    are the second layer of defense.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Reject unsafe API requests whose CSRF header does not match the cookie.

        Args:
            request (Request): The incoming request.
            call_next (RequestResponseEndpoint): The downstream handler.

        Returns:
            Response: The downstream response, or a 403 on CSRF failure.
        """
        if request.url.path.startswith("/api") and request.method in UNSAFE_METHODS:
            cookie = request.cookies.get(CSRF_COOKIE)
            header = request.headers.get(CSRF_HEADER)
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                return JSONResponse(
                    {"detail": "CSRF token missing or invalid"}, status_code=403
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.url.path.startswith("/api"):
            # Personal records must not be written to a browser's disk cache or
            # held by an intermediary proxy; a cached /api/auth/status would
            # also let a stale "not authenticated" outlive the login that
            # replaced it (G-51). `setdefault` keeps the stricter
            # `private, no-store` that file downloads already declare (G-11).
            response.headers.setdefault("Cache-Control", "no-store")
        if CSRF_COOKIE not in request.cookies:
            secure = get_settings().trust_proxy or request.url.scheme == "https"
            response.set_cookie(
                CSRF_COOKIE,
                new_token(),
                samesite="lax",
                httponly=False,  # the SPA must read it to echo it back
                secure=secure,
                path="/",
            )
        return response
