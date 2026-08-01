"""Tag routes: CRUD, and assignment to a person (Phase 2, "Organizing people")."""

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas.tag import TagCreate, TagOut, TagUpdate
from app.services.tag_service import TagService

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagOut])
async def list_tags(_: CurrentUser, db: DbSession) -> list[TagOut]:
    """List every tag with how many people wear it ("Organizing people")."""
    return await TagService(db).list()


@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(data: TagCreate, _: CurrentUser, db: DbSession) -> TagOut:
    """Create a tag."""
    return await TagService(db).create(data)


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def rename_tag(tag_id: int, data: TagUpdate, _: CurrentUser, db: DbSession) -> TagOut:
    """Rename a tag."""
    return await TagService(db).rename(tag_id, data)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, _: CurrentUser, db: DbSession) -> None:
    """Delete a tag; assignments disappear with it, people do not."""
    await TagService(db).delete(tag_id)


@router.post("/people/{person_id}/tags", response_model=TagOut, status_code=201)
async def assign_tag(person_id: int, data: TagCreate, _: CurrentUser, db: DbSession) -> TagOut:
    """Attach a tag to a person, creating it first if the name is new (create-on-type)."""
    return await TagService(db).assign(person_id, data.name)


@router.delete("/people/{person_id}/tags/{tag_id}", status_code=204)
async def unassign_tag(person_id: int, tag_id: int, _: CurrentUser, db: DbSession) -> None:
    """Detach a tag from a person."""
    await TagService(db).unassign(person_id, tag_id)
