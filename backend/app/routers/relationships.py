"""Relationship routes: create, remove (Epic E, Phase 2)."""

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas.relationship import RelationshipCreate, RelationshipOut
from app.services.relationship_service import RelationshipService

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post("", response_model=RelationshipOut, status_code=201)
async def create_relationship(
    data: RelationshipCreate, _: CurrentUser, db: DbSession
) -> RelationshipOut:
    """Create a relationship between two people (FR-22/23/24)."""
    return await RelationshipService(db).create(data)


@router.delete("/{relationship_id}", status_code=204)
async def remove_relationship(relationship_id: int, _: CurrentUser, db: DbSession) -> None:
    """Remove a relationship from either person's record (FR-25)."""
    await RelationshipService(db).remove(relationship_id)
