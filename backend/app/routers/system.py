"""System routes: health check."""

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import DbSession

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health(db: DbSession) -> dict[str, str]:
    """Readiness probe: verifies database connectivity (G-14)."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
