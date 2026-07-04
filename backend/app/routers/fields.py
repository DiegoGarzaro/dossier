"""Field routes: add, edit, remove, reorder (Epic C)."""

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas.field import FieldCreate, FieldOut, FieldUpdate, ReorderRequest
from app.services.field_service import FieldService

router = APIRouter(tags=["fields"])


@router.post("/people/{person_id}/fields", response_model=FieldOut, status_code=201)
async def add_field(
    person_id: int, data: FieldCreate, _: CurrentUser, db: DbSession
) -> FieldOut:
    """Add a custom field to a person (FR-11)."""
    return FieldOut.model_validate(await FieldService(db).add(person_id, data))


@router.patch("/fields/{field_id}", response_model=FieldOut)
async def update_field(field_id: int, data: FieldUpdate, _: CurrentUser, db: DbSession) -> FieldOut:
    """Edit a field's label, value, type, or pinned flag (FR-15/16)."""
    return FieldOut.model_validate(await FieldService(db).update(field_id, data))


@router.delete("/fields/{field_id}", status_code=204)
async def remove_field(field_id: int, _: CurrentUser, db: DbSession) -> None:
    """Remove a field (FR-15)."""
    await FieldService(db).remove(field_id)


@router.post("/people/{person_id}/fields/reorder", response_model=list[FieldOut])
async def reorder_fields(
    person_id: int, data: ReorderRequest, _: CurrentUser, db: DbSession
) -> list[FieldOut]:
    """Apply new sort positions to a person's fields (FR-15)."""
    fields = await FieldService(db).reorder(person_id, data)
    return [FieldOut.model_validate(field) for field in fields]
