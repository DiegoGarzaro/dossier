"""People routes: index, ID-card detail, create/edit/delete, photo (Epic B)."""

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.enums import FieldType
from app.deps import CurrentUser, DbSession
from app.models import Person
from app.schemas.field import FieldOut
from app.schemas.person import PersonCreate, PersonDetail, PersonSummary, PersonUpdate
from app.schemas.relationship import RelationshipOut, TreeOut
from app.services.people_service import PeopleService
from app.services.relationship_service import RelationshipService
from app.services.vcard_service import VCardService

router = APIRouter(prefix="/people", tags=["people"])


def _summary(person: Person) -> PersonSummary:
    """Build a grid entry from a person with loaded fields.

    Args:
        person (Person): The person with fields eagerly loaded.

    Returns:
        PersonSummary: The index-grid representation.
    """
    # Sensitive values are masked-by-default in the UI (SEC-7); the grid
    # preview has no reveal control, so they are excluded entirely.
    pinned = [
        field
        for field in person.fields
        if field.is_pinned and field.value and field.type != FieldType.sensitive
    ]
    return PersonSummary(
        id=person.id,
        full_name=person.full_name,
        has_photo=person.photo_path is not None,
        updated_at=person.updated_at,
        pinned_fields=[FieldOut.model_validate(field) for field in pinned[:2]],
    )


def _detail(person: Person, relationships: list[RelationshipOut]) -> PersonDetail:
    """Build the full ID-card payload.

    Args:
        person (Person): The person with fields and documents loaded.
        relationships (list[RelationshipOut]): The person's resolved relationships.

    Returns:
        PersonDetail: The detail representation.
    """
    detail = PersonDetail.model_validate(person)
    detail.has_photo = person.photo_path is not None
    detail.relationships = relationships
    return detail


@router.get("", response_model=list[PersonSummary])
async def list_people(_: CurrentUser, db: DbSession, q: str | None = None) -> list[PersonSummary]:
    """List people for the index grid, optionally filtered by name (FR-10/26)."""
    return [_summary(person) for person in await PeopleService(db).list(q)]


@router.post("", response_model=PersonDetail, status_code=201)
async def create_person(data: PersonCreate, _: CurrentUser, db: DbSession) -> PersonDetail:
    """Create a person with suggested pinned fields (FR-6/17)."""
    person = await PeopleService(db).create(data)
    return await get_person(person.id, _, db)


@router.get("/{person_id}", response_model=PersonDetail)
async def get_person(person_id: int, _: CurrentUser, db: DbSession) -> PersonDetail:
    """Fetch the full ID-card payload (FR-7)."""
    person = await PeopleService(db).get_detail(person_id)
    relationships = await RelationshipService(db).list_for_person(person_id)
    return _detail(person, relationships)


@router.patch("/{person_id}", response_model=PersonDetail)
async def update_person(
    person_id: int, data: PersonUpdate, _: CurrentUser, db: DbSession
) -> PersonDetail:
    """Rename a person (FR-8)."""
    await PeopleService(db).update(person_id, data)
    return await get_person(person_id, _, db)


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: int, _: CurrentUser, db: DbSession) -> None:
    """Delete a person and all associated data (FR-9)."""
    await PeopleService(db).delete(person_id)


@router.put("/{person_id}/photo", response_model=PersonDetail)
async def set_photo(
    person_id: int, file: UploadFile, _: CurrentUser, db: DbSession
) -> PersonDetail:
    """Upload or replace the profile photo (FR-8)."""
    await PeopleService(db).set_photo(person_id, file)
    return await get_person(person_id, _, db)


@router.get("/{person_id}/photo")
async def get_photo(person_id: int, _: CurrentUser, db: DbSession) -> FileResponse:
    """Serve the profile photo inline with its verified image content-type."""
    path, mime = await PeopleService(db).get_photo_path(person_id)
    return FileResponse(path, media_type=mime, headers={"Cache-Control": "private, no-store"})


@router.get("/{person_id}/tree", response_model=TreeOut)
async def get_tree(person_id: int, _: CurrentUser, db: DbSession) -> TreeOut:
    """Fetch a person's connected relationship graph for the tree view (Phase 2b)."""
    return await RelationshipService(db).tree(person_id)


@router.get("/{person_id}/vcard")
async def get_vcard(person_id: int, _: CurrentUser, db: DbSession) -> Response:
    """Export a person as a vCard (Phase 3, new idea)."""
    vcard, filename = await VCardService(db).build(person_id)
    return Response(
        content=vcard,
        media_type="text/vcard",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
