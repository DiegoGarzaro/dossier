"""Encrypted backup / restore routes (Phase 3, closes G-36).

Both routes are POST even though `/backup` only reads: a GET would put the
passphrase in the URL, where it lands in server access logs and browser
history. `/restore` takes multipart because it carries a file; it is
deliberately **not** run through `sniff_mime`/`ALLOWED_DOCUMENT_TYPES` — a
`.dossier` backup is not a document upload and that allow-list would reject
it. Its size cap is enforced while streaming the upload in, not by trusting
`Content-Length` or buffering an unbounded body first.
"""

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import Response

from app.config import get_settings
from app.core.errors import PayloadTooLargeError
from app.deps import CurrentUser, DbSession
from app.schemas.backup import BackupRequest
from app.schemas.export import ImportReport
from app.services.backup_service import BackupService

router = APIRouter(tags=["backup"])

_CHUNK_SIZE = 1024 * 1024


@router.post("/backup")
async def create_backup(data: BackupRequest, _: CurrentUser, db: DbSession) -> Response:
    """Create an encrypted backup archive of the full vault: data and uploaded files (G-36)."""
    blob, filename = await BackupService(db).create(data.passphrase)
    return Response(
        content=blob,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/restore", response_model=ImportReport)
async def restore_backup(
    file: UploadFile, _: CurrentUser, db: DbSession, passphrase: str = Form(...)
) -> ImportReport:
    """Restore an encrypted backup archive (G-36).

    Additive only, same as a plain JSON import: existing people are never
    overwritten or deleted.
    """
    settings = get_settings()
    size = 0
    chunks: list[bytes] = []
    while chunk := await file.read(_CHUNK_SIZE):
        size += len(chunk)
        if size > settings.max_backup_bytes:
            raise PayloadTooLargeError(f"Backup file exceeds the {settings.max_backup_mb} MB limit")
        chunks.append(chunk)
    return await BackupService(db).restore(b"".join(chunks), passphrase)
