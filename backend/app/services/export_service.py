"""JSON export of a person or the whole vault (Phase 3, FR-30 / G3).

Two scopes share one envelope shape so an importer only has to learn one
format. Values of `sensitive`-type fields are withheld unless the caller
explicitly opts in (SEC-7): the safe default keeps secrets out of a file
that, by design, leaves the app.

The export deliberately carries **no file bytes** — uploaded documents and
photos stay on the `/data` volume and are covered by the directory backup
procedure (G1/G2). This file is the structured data, not the blobs.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import FieldType
from app.core.files import download_filename
from app.models import Document, Person, PersonField, Relationship
from app.models.base import utcnow
from app.repositories.people_repo import PeopleRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.export import (
    ExportDocument,
    ExportEnvelope,
    ExportField,
    ExportPerson,
    ExportRelationship,
    ExportScope,
)
from app.services.people_service import PeopleService


def _field(field: PersonField, include_sensitive: bool) -> ExportField:
    """Convert a stored field, withholding sensitive values unless opted in.

    Args:
        field (PersonField): The stored field.
        include_sensitive (bool): Whether `sensitive` values may be exported.

    Returns:
        ExportField: The exportable field; `value_omitted` flags a withheld value.
    """
    withheld = field.type == FieldType.sensitive and not include_sensitive
    return ExportField(
        label=field.label,
        value=None if withheld else field.value,
        type=field.type,
        is_pinned=field.is_pinned,
        is_system=field.is_system,
        position=field.position,
        value_omitted=withheld,
    )


def _document(document: Document, include_storage_paths: bool) -> ExportDocument:
    """Convert stored document metadata, optionally including its storage path.

    Args:
        document (Document): The stored document.
        include_storage_paths (bool): Whether to include the on-disk random
            filename (SEC-6) — only true for an encrypted backup archive.

    Returns:
        ExportDocument: The exportable document metadata.
    """
    return ExportDocument(
        title=document.title,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        uploaded_at=document.uploaded_at,
        storage_path=document.storage_path if include_storage_paths else None,
    )


def _person(
    person: Person, include_sensitive: bool, include_storage_paths: bool = False
) -> ExportPerson:
    """Convert a person with their fields, document metadata, tags, and favorite flag.

    Args:
        person (Person): The person with fields, documents, and tags loaded.
        include_sensitive (bool): Whether `sensitive` values may be exported.
        include_storage_paths (bool): Whether to include documents' and the
            photo's on-disk random filenames (SEC-6) — only true for an
            encrypted backup archive, which carries the file bytes too and
            needs the link to restore them.

    Returns:
        ExportPerson: The exportable person record.
    """
    return ExportPerson(
        id=person.id,
        full_name=person.full_name,
        has_photo=person.photo_path is not None,
        created_at=person.created_at,
        updated_at=person.updated_at,
        is_favorite=person.is_favorite,
        tags=[tag.name for tag in person.tags],
        fields=[_field(field, include_sensitive) for field in person.fields],
        documents=[_document(document, include_storage_paths) for document in person.documents],
        photo_path=person.photo_path if include_storage_paths else None,
    )


def _relationship(link: Relationship) -> ExportRelationship:
    """Convert a relationship, denormalizing both people's names.

    Args:
        link (Relationship): The stored (canonical) relationship row.

    Returns:
        ExportRelationship: The exportable link.
    """
    return ExportRelationship(
        person_a_id=link.person_a_id,
        person_a_name=link.person_a.full_name,
        person_b_id=link.person_b_id,
        person_b_name=link.person_b.full_name,
        type=link.type,
        custom_label=link.custom_label,
        role_a=link.role_a,
        role_b=link.role_b,
    )


class ExportService:
    """Builds portable JSON exports (FR-30 / G3)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._people_service = PeopleService(session)
        self._people = PeopleRepository(session)
        self._relationships = RelationshipRepository(session)

    async def export_person(
        self,
        person_id: int,
        include_sensitive: bool = False,
        include_storage_paths: bool = False,
    ) -> tuple[ExportEnvelope, str]:
        """Export a single person and the links that touch them.

        Args:
            person_id (int): The person id.
            include_sensitive (bool): Opt in to exporting `sensitive` field
                values in plaintext; defaults to withholding them (SEC-7).
            include_storage_paths (bool): Opt in to exporting documents'
                and the photo's on-disk random filenames (SEC-6); defaults
                to withholding them. Only `BackupService` sets this True —
                the plain JSON export endpoints never do.

        Returns:
            tuple[ExportEnvelope, str]: (envelope, download filename).

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people_service.get_detail(person_id)
        links = await self._relationships.list_for_person(person_id)
        envelope = self._envelope(
            scope="person",
            include_sensitive=include_sensitive,
            people=[_person(person, include_sensitive, include_storage_paths)],
            links=links,
        )
        return envelope, download_filename(person.full_name, ".json", fallback="person")

    async def export_dataset(
        self, include_sensitive: bool = False, include_storage_paths: bool = False
    ) -> tuple[ExportEnvelope, str]:
        """Export every person and every relationship in the vault.

        Args:
            include_sensitive (bool): Opt in to exporting `sensitive` field
                values in plaintext; defaults to withholding them (SEC-7).
            include_storage_paths (bool): Opt in to exporting documents'
                and photos' on-disk random filenames (SEC-6); defaults to
                withholding them. Only `BackupService` sets this True — the
                plain JSON export endpoints never do.

        Returns:
            tuple[ExportEnvelope, str]: (envelope, download filename).
        """
        people = await self._people.list_with_details()
        links = await self._relationships.list_all()
        envelope = self._envelope(
            scope="dataset",
            include_sensitive=include_sensitive,
            people=[
                _person(person, include_sensitive, include_storage_paths) for person in people
            ],
            links=links,
        )
        stamp = datetime.now().strftime("%Y-%m-%d")
        return envelope, f"dossier-export-{stamp}.json"

    def _envelope(
        self,
        scope: ExportScope,
        include_sensitive: bool,
        people: list[ExportPerson],
        links: list[Relationship],
    ) -> ExportEnvelope:
        """Wrap exported records in the versioned envelope.

        Args:
            scope (ExportScope): Whether this is a person or dataset export.
            include_sensitive (bool): Whether sensitive values were included.
            people (list[ExportPerson]): The exported people.
            links (list[Relationship]): The stored relationships to include.

        Returns:
            ExportEnvelope: The complete export payload.
        """
        return ExportEnvelope(
            exported_at=utcnow(),
            scope=scope,
            includes_sensitive_values=include_sensitive,
            people=people,
            relationships=[_relationship(link) for link in links],
        )
