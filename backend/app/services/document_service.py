"""Document business logic: safe upload, download resolution, deletion (Epic D)."""

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.files import sanitize_filename, sniff_mime
from app.models import Document
from app.repositories.document_repo import DocumentRepository
from app.repositories.people_repo import PeopleRepository


class DocumentService:
    """Orchestrates document upload, download, and deletion."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._documents = DocumentRepository(session)
        self._people = PeopleRepository(session)

    async def upload(self, person_id: int, upload: UploadFile, title: str | None) -> Document:
        """Validate and store an uploaded file, then persist its metadata (FR-18/19/20).

        The file is streamed to disk under a random name; the client filename is
        kept only as display metadata (SEC-6).

        Args:
            person_id (int): The owning person id.
            upload (UploadFile): The uploaded file.
            title (str | None): Optional display title; defaults to the filename.

        Returns:
            Document: The persisted document metadata.

        Raises:
            NotFoundError: If the person does not exist.
            InvalidInputError: If the file type is not allowed.
            PayloadTooLargeError: If the file exceeds the upload limit.
        """
        if await self._people.get(person_id) is None:
            raise NotFoundError("Person not found")
        settings = get_settings()
        original = sanitize_filename(upload.filename or "upload")
        head = await upload.read(16)
        mime = sniff_mime(original, head)

        person_dir = settings.uploads_dir / str(person_id)
        person_dir.mkdir(parents=True, exist_ok=True)
        relative = f"{person_id}/{uuid.uuid4().hex}{Path(original).suffix.lower()}"
        destination = settings.uploads_dir / relative

        size = len(head)
        with destination.open("wb") as target:
            target.write(head)
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    target.close()
                    destination.unlink(missing_ok=True)
                    raise PayloadTooLargeError(
                        f"File exceeds the {settings.max_upload_mb} MB limit"
                    )
                target.write(chunk)

        return await self._documents.add(
            Document(
                person_id=person_id,
                title=title or Path(original).stem,
                original_filename=original,
                mime_type=mime,
                size_bytes=size,
                storage_path=relative,
            )
        )

    async def get_download(self, document_id: int) -> tuple[Document, Path]:
        """Resolve a document and its file path for download (FR-21).

        Args:
            document_id (int): The document id.

        Returns:
            tuple[Document, Path]: The metadata and the absolute file path.

        Raises:
            NotFoundError: If the document or its file does not exist.
        """
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        path = get_settings().uploads_dir / document.storage_path
        if not path.is_file():
            raise NotFoundError("Stored file is missing")
        return document, path

    async def rename(self, document_id: int, title: str) -> Document:
        """Rename a document (FR-D2).

        Args:
            document_id (int): The document id.
            title (str): The new display title.

        Returns:
            Document: The updated document.

        Raises:
            NotFoundError: If the document does not exist.
        """
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        document.title = title
        return document

    async def delete(self, document_id: int) -> None:
        """Delete a document's file and metadata (FR-21).

        Args:
            document_id (int): The document id.

        Returns:
            None

        Raises:
            NotFoundError: If the document does not exist.
        """
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        path = get_settings().uploads_dir / document.storage_path
        await self._documents.delete(document)
        path.unlink(missing_ok=True)
