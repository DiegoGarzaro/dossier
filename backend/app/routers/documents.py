"""Document routes: upload, download, rename, delete (Epic D)."""

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse

from app.deps import CurrentUser, DbSession
from app.schemas.document import DocumentOut, DocumentUpdate
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


@router.post("/people/{person_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    person_id: int,
    file: UploadFile,
    _: CurrentUser,
    db: DbSession,
    title: str | None = Form(default=None),
) -> DocumentOut:
    """Upload a file to a person's record (FR-18/19/20)."""
    return DocumentOut.model_validate(await DocumentService(db).upload(person_id, file, title))


@router.get("/documents/{document_id}/download")
async def download_document(document_id: int, _: CurrentUser, db: DbSession) -> FileResponse:
    """Stream a document as an attachment download (FR-21 / SEC-6)."""
    document, path = await DocumentService(db).get_download(document_id)
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.original_filename,
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-store"},
    )


@router.patch("/documents/{document_id}", response_model=DocumentOut)
async def rename_document(
    document_id: int, data: DocumentUpdate, _: CurrentUser, db: DbSession
) -> DocumentOut:
    """Rename a document (FR-D2)."""
    return DocumentOut.model_validate(await DocumentService(db).rename(document_id, data.title))


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: int, _: CurrentUser, db: DbSession) -> None:
    """Delete a document's file and metadata (FR-21)."""
    await DocumentService(db).delete(document_id)
