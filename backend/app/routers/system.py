"""System routes: health check, at-a-glance vault summary (G-36)."""

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import CurrentUser, DbSession
from app.schemas.system import SystemSummary
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health(db: DbSession) -> dict[str, str]:
    """Readiness probe: verifies database connectivity (G-14)."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/summary", response_model=SystemSummary)
async def summary(_: CurrentUser, db: DbSession) -> SystemSummary:
    """Record counts, storage usage, and the last backup time (G-36)."""
    return await SystemService(db).summary()
