"""Test fixtures: isolated temp data dir, migrated schema, authed client."""

import os
import tempfile

# Point the app at an isolated data dir BEFORE importing it.
os.environ["DOSSIER_DATA_DIR"] = tempfile.mkdtemp(prefix="dossier-test-")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import app, run_migrations  # noqa: E402

ADMIN = {"username": "admin", "password": "correct-horse-battery"}


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    """Create the data directory and run migrations once per test session."""
    settings = get_settings()
    settings.photos_dir.mkdir(parents=True, exist_ok=True)
    run_migrations()


@pytest.fixture
async def client() -> AsyncClient:
    """An anonymous API client with a fresh cookie jar.

    Yields:
        AsyncClient: Client bound to the app via ASGI transport.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _csrf(client: AsyncClient) -> str:
    """Fetch the CSRF cookie by hitting a safe endpoint.

    Args:
        client (AsyncClient): The client whose jar receives the cookie.

    Returns:
        str: The CSRF token value.
    """
    await client.get("/api/auth/status")
    return client.cookies["dossier_csrf"]


@pytest.fixture(scope="session")
async def authed_client() -> AsyncClient:
    """A client that has completed first-run setup (or logged in) with CSRF wired.

    Yields:
        AsyncClient: Authenticated client sending X-CSRF-Token by default.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        token = await _csrf(c)
        c.headers["x-csrf-token"] = token
        status = (await c.get("/api/auth/status")).json()
        if status["initialized"]:
            response = await c.post("/api/auth/login", json=ADMIN)
        else:
            response = await c.post("/api/auth/setup", json=ADMIN)
        assert response.status_code == 200, response.text
        yield c
