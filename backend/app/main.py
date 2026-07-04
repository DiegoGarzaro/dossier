"""Application entrypoint: app factory, migrations on startup, SPA serving."""

from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from alembic import command
from app.config import get_settings
from app.core.errors import AppError
from app.db import SessionLocal
from app.middleware import CSRFMiddleware
from app.repositories.session_repo import SessionRepository
from app.routers import auth, documents, fields, people, system

BACKEND_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"


def run_migrations() -> None:
    """Run Alembic migrations to head (NFR-8).

    Returns:
        None
    """
    config = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare the data directory and schema before serving."""
    settings = get_settings()
    settings.photos_dir.mkdir(parents=True, exist_ok=True)
    run_migrations()
    async with SessionLocal() as session:
        await SessionRepository(session).purge_expired()
        await session.commit()
    yield


app = FastAPI(title="Dossier", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
app.add_middleware(CSRFMiddleware)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Translate domain errors into HTTP responses.

    Args:
        _ (Request): The request (unused).
        exc (AppError): The raised domain error.

    Returns:
        JSONResponse: An error body with the mapped status code.
    """
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


for router in (auth.router, people.router, fields.router, documents.router, system.router):
    app.include_router(router, prefix="/api")


if (STATIC_DIR / "index.html").is_file():  # built frontend present (production image)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """Serve the SPA bundle with an index.html fallback for client routes."""
        if full_path.startswith("api"):
            raise HTTPException(status_code=404)
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(STATIC_DIR):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
