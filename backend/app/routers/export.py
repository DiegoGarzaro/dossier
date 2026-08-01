"""JSON export routes: one person or the whole vault (Phase 3, FR-30 / G3)."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.deps import CurrentUser, DbSession
from app.schemas.export import ExportEnvelope, ImportReport
from app.services.export_service import ExportService
from app.services.import_service import ImportService

router = APIRouter(tags=["export"])

# `ExportDocument.storage_path` / `ExportPerson.photo_path` exist on the model
# so `BackupService` can populate and round-trip them through the very same
# schema (G-36). The **plain** JSON export never sets them (SEC-6) — and,
# since a `None`-valued field still serializes as a `null` key by default,
# they are also excluded from the wire payload here so the key itself never
# appears, not just the value.
_PLAIN_EXPORT_EXCLUDE = {
    "people": {
        "__all__": {
            "photo_path": True,
            "documents": {"__all__": {"storage_path": True}},
        }
    }
}


def _download(envelope: ExportEnvelope, filename: str) -> Response:
    """Shape an export envelope as a JSON file download.

    Args:
        envelope (ExportEnvelope): The export payload.
        filename (str): The ASCII-safe download filename.

    Returns:
        Response: An attachment response with nosniff and no-store headers.
    """
    return Response(
        content=envelope.model_dump_json(indent=2, exclude=_PLAIN_EXPORT_EXCLUDE),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/people/{person_id}/export")
async def export_person(
    person_id: int, _: CurrentUser, db: DbSession, include_sensitive: bool = False
) -> Response:
    """Export one person as JSON (FR-30).

    `sensitive` field values are withheld unless `include_sensitive=true` is
    passed explicitly (SEC-7).
    """
    envelope, filename = await ExportService(db).export_person(person_id, include_sensitive)
    return _download(envelope, filename)


@router.get("/export")
async def export_dataset(
    _: CurrentUser, db: DbSession, include_sensitive: bool = False
) -> Response:
    """Export every person and relationship as one JSON file (FR-30 / G3).

    `sensitive` field values are withheld unless `include_sensitive=true` is
    passed explicitly (SEC-7).
    """
    envelope, filename = await ExportService(db).export_dataset(include_sensitive)
    return _download(envelope, filename)


@router.post("/import", response_model=ImportReport)
async def import_dataset(
    envelope: ExportEnvelope, _: CurrentUser, db: DbSession
) -> ImportReport:
    """Restore an export file into the vault (FR-30 / G3).

    Additive only: existing people are never overwritten or deleted, and a
    person whose name is already on file is skipped.
    """
    return await ImportService(db).apply(envelope)
