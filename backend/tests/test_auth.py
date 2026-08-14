"""Auth flow tests: guard, CSRF, setup-once, login."""

from httpx import AsyncClient

from app.config import get_settings
from app.db import SessionLocal
from app.repositories.user_repo import UserRepository
from tests.conftest import ADMIN


async def test_data_routes_require_auth(client: AsyncClient) -> None:
    """Every data route rejects unauthenticated access (FR-1)."""
    assert (await client.get("/api/people")).status_code == 401


async def test_unsafe_requests_require_csrf(client: AsyncClient) -> None:
    """State-changing requests without the CSRF header are rejected (SEC-3)."""
    response = await client.post("/api/auth/login", json=ADMIN)
    assert response.status_code == 403


async def test_setup_only_once(authed_client: AsyncClient) -> None:
    """Setup refuses to run twice (FR-5)."""
    response = await authed_client.post(
        "/api/auth/setup", json={"username": "intruder", "password": "password123"}
    )
    assert response.status_code == 409


async def test_login_rejects_bad_credentials(client: AsyncClient, authed_client) -> None:
    """Wrong passwords yield 401 without leaking which part was wrong."""
    await client.get("/api/auth/status")
    client.headers["x-csrf-token"] = client.cookies["dossier_csrf"]
    response = await client.post(
        "/api/auth/login", json={"username": ADMIN["username"], "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_status_reflects_session(authed_client: AsyncClient) -> None:
    """Status reports the authenticated user."""
    status = (await authed_client.get("/api/auth/status")).json()
    assert status == {
        "initialized": True,
        "authenticated": True,
        "username": ADMIN["username"],
    }


async def _reset_lockout() -> None:
    """Clear the admin's failed-attempt counter so this test doesn't leak
    lockout state into other tests sharing the session-scoped database."""
    async with SessionLocal() as session:
        user = await UserRepository(session).get_by_username(ADMIN["username"])
        assert user is not None
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()


async def test_login_lockout_after_repeated_failures(client: AsyncClient) -> None:
    """Repeated failed logins lock the account until the cooldown expires (G-07)."""
    await _reset_lockout()
    await client.get("/api/auth/status")
    client.headers["x-csrf-token"] = client.cookies["dossier_csrf"]
    bad = {"username": ADMIN["username"], "password": "wrong-password"}

    try:
        for _ in range(get_settings().login_max_attempts):
            response = await client.post("/api/auth/login", json=bad)
            assert response.status_code == 401

        locked = await client.post("/api/auth/login", json=bad)
        assert locked.status_code == 429

        # Even the correct password is rejected while locked.
        still_locked = await client.post("/api/auth/login", json=ADMIN)
        assert still_locked.status_code == 429
    finally:
        await _reset_lockout()

    recovered = await client.post("/api/auth/login", json=ADMIN)
    assert recovered.status_code == 200


async def test_api_responses_are_not_cacheable(
    authed_client: AsyncClient, client: AsyncClient
) -> None:
    """Every /api response carries `no-store` (G-51).

    Personal records must never sit in a browser's disk cache or in an
    intermediary proxy, and a cached `/api/auth/status` would let a stale
    "not authenticated" answer outlive the session that replaced it.
    """
    for path in ("/api/auth/status", "/api/people", "/api/tags"):
        response = await authed_client.get(path)
        assert response.status_code == 200, path
        assert response.headers["cache-control"] == "no-store", path

    # An anonymous status probe is just as sensitive: a cached "not
    # authenticated" would survive the login that replaced it (G-48).
    anonymous = await client.get("/api/auth/status")
    assert anonymous.headers["cache-control"] == "no-store"


async def test_spa_shell_is_revalidated_but_hashed_assets_are_cacheable(
    client: AsyncClient,
) -> None:
    """`index.html` must never be served stale (G-58).

    The shell names content-hashed bundles, so a cached copy pins the browser
    to an old build — the app silently keeps rendering the previous release
    after a deploy. The hashed assets themselves are immutable by construction.
    """
    shell = await client.get("/")
    assert shell.status_code == 200
    assert shell.headers["cache-control"] == "no-cache"

    asset = await client.get("/fonts/inter-400.woff2")
    assert asset.status_code == 200
    assert "immutable" in asset.headers["cache-control"]
