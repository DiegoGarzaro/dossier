"""Auth flow tests: guard, CSRF, setup-once, login."""

from httpx import AsyncClient

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
