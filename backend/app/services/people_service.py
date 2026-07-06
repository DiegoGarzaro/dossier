"""People business logic: CRUD, photo handling, cascade cleanup (Epic B)."""

import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.files import ALLOWED_DOCUMENT_TYPES, IMAGE_TYPES, sniff_mime
from app.models import Person, PersonField
from app.repositories.people_repo import PeopleRepository
from app.schemas.person import PersonCreate, PersonUpdate

# Fields suggested on creation, matching the reference mockup (FR-17).
DEFAULT_PINNED_LABELS = ("Document number", "Address", "Nationality")

_IMAGE_ALLOWED = {
    mime: spec for mime, spec in ALLOWED_DOCUMENT_TYPES.items() if mime in IMAGE_TYPES
}


class PeopleService:
    """Orchestrates person operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._people = PeopleRepository(session)

    async def list(self, query: str | None = None) -> list[Person]:
        """List people for the index grid, optionally filtered by name (FR-10/26).

        Args:
            query (str | None): Optional name search.

        Returns:
            list[Person]: People ordered by name with fields loaded.
        """
        return await self._people.list(query)

    async def create(self, data: PersonCreate) -> Person:
        """Create a person with pre-populated empty pinned fields (FR-6/17).

        Args:
            data (PersonCreate): The creation payload.

        Returns:
            Person: The created person.
        """
        person = Person(full_name=data.full_name)
        person.fields = [
            PersonField(label=label, value=None, is_pinned=True, is_system=True, position=index)
            for index, label in enumerate(DEFAULT_PINNED_LABELS)
        ]
        return await self._people.add(person)

    async def get_detail(self, person_id: int) -> Person:
        """Fetch the full ID-card payload (FR-7).

        Args:
            person_id (int): The person id.

        Returns:
            Person: The person with fields and documents loaded.

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people.get_with_details(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        return person

    async def update(self, person_id: int, data: PersonUpdate) -> Person:
        """Rename a person (FR-8).

        Args:
            person_id (int): The person id.
            data (PersonUpdate): The update payload.

        Returns:
            Person: The updated person.

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people.get(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        person.full_name = data.full_name
        return person

    async def delete(self, person_id: int) -> None:
        """Delete a person and their files; DB rows cascade (FR-9).

        Args:
            person_id (int): The person id.

        Returns:
            None

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people.get_with_details(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        settings = get_settings()
        paths = [doc.storage_path for doc in person.documents]
        if person.photo_path:
            paths.append(person.photo_path)
        await self._people.delete(person)
        for relative in paths:
            (settings.uploads_dir / relative).unlink(missing_ok=True)
        person_dir = settings.uploads_dir / str(person_id)
        if person_dir.is_dir():
            shutil.rmtree(person_dir, ignore_errors=True)

    async def set_photo(self, person_id: int, upload: UploadFile) -> Person:
        """Store or replace a person's profile photo (FR-8).

        Args:
            person_id (int): The person id.
            upload (UploadFile): The uploaded image (PNG, JPG, or WEBP).

        Returns:
            Person: The updated person.

        Raises:
            NotFoundError: If the person does not exist.
            InvalidInputError: If the file is not an allowed image.
            PayloadTooLargeError: If the file exceeds the upload limit.
        """
        person = await self._people.get(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        settings = get_settings()
        head = await upload.read(16)
        sniff_mime(upload.filename or "", head, allowed=_IMAGE_ALLOWED)  # validate only
        extension = Path(upload.filename or "").suffix.lower()

        settings.photos_dir.mkdir(parents=True, exist_ok=True)
        relative = f"_photos/{uuid.uuid4().hex}{extension}"
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

        if person.photo_path:
            (settings.uploads_dir / person.photo_path).unlink(missing_ok=True)
        person.photo_path = relative
        return person

    async def get_photo_path(self, person_id: int) -> tuple[Path, str]:
        """Resolve the photo file path and MIME type for serving.

        Args:
            person_id (int): The person id.

        Returns:
            tuple[Path, str]: Absolute file path and its MIME type.

        Raises:
            NotFoundError: If the person or photo does not exist.
        """
        person = await self._people.get(person_id)
        if person is None or not person.photo_path:
            raise NotFoundError("Photo not found")
        path = get_settings().uploads_dir / person.photo_path
        if not path.is_file():
            raise NotFoundError("Photo not found")
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "application/octet-stream")
        return path, mime
