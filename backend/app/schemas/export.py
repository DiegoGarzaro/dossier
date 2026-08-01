"""JSON export schemas — the portable file format (Phase 3, FR-30 / G3).

The envelope is versioned so a future import can recognize what it is
reading. Bump `EXPORT_SCHEMA_VERSION` whenever the shape changes in a way
an importer must react to.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import FieldType, RelationshipType

EXPORT_SCHEMA_VERSION = 3

ExportScope = Literal["person", "dataset"]


class ExportField(BaseModel):
    """One custom field in an export.

    `value_omitted` marks a `sensitive` field whose value was withheld
    because the export did not opt into sensitive values (SEC-7): the field
    still travels (label, type, flags) so the record's shape survives a
    round-trip, but the secret does not.
    """

    # Bounds mirror FieldCreate: the same model parses untrusted import files.
    label: str = Field(min_length=1, max_length=255)
    value: str | None = Field(default=None, max_length=10_000)
    type: FieldType
    is_pinned: bool
    is_system: bool
    position: int
    value_omitted: bool = False


class ExportDocument(BaseModel):
    """Metadata for an uploaded document.

    The file bytes are **not** part of the JSON — they live on the `/data`
    volume and are covered by the directory backup (G1/G2), or, for a full
    encrypted backup, inside the same archive (G-36). `storage_path` is the
    random on-disk filename: the **plain** JSON export deliberately leaves it
    `None` so it never leaves over the API (SEC-6); only the encrypted
    backup archive (`BackupService`) populates it, since that archive
    carries the file bytes too and needs the link to restore them.
    """

    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    storage_path: str | None = None


class ExportPerson(BaseModel):
    """One person with their fields, document metadata, tags, and favorite flag.

    `tags` carries tag **names**, not ids — ids are meaningless across vaults,
    while a name can be matched (and find-or-created) on import. `tags` and
    `is_favorite` default so a schema-v1 file (produced before either
    existed) still validates and imports cleanly; `photo_path` defaults so a
    v1 or v2 file (produced before it existed) does too. Like
    `ExportDocument.storage_path`, `photo_path` stays `None` in the plain
    JSON export (SEC-6) and is populated only inside an encrypted backup.
    """

    id: int
    full_name: str = Field(min_length=1, max_length=255)
    has_photo: bool
    created_at: datetime
    updated_at: datetime
    is_favorite: bool = False
    tags: list[str] = []
    fields: list[ExportField]
    documents: list[ExportDocument]
    photo_path: str | None = None


class ExportRelationship(BaseModel):
    """A relationship in its stored canonical direction (Architecture §4.2).

    Names are denormalized alongside the ids so the file is readable on its
    own and an importer can match people even if ids shift.
    """

    person_a_id: int
    person_a_name: str
    person_b_id: int
    person_b_name: str
    type: RelationshipType
    custom_label: str | None = None
    role_a: str | None = None
    role_b: str | None = None


class ExportEnvelope(BaseModel):
    """The complete export file: metadata header + people + relationships.

    Doubles as the **import** request body, so it stays permissive about
    `generator` and `schema_version` — the import service decides whether a
    file is acceptable and answers with a friendly domain error rather than a
    422 shape complaint.
    """

    schema_version: int = EXPORT_SCHEMA_VERSION
    generator: str = "dossier"
    exported_at: datetime
    scope: ExportScope
    includes_sensitive_values: bool
    people: list[ExportPerson]
    relationships: list[ExportRelationship]


class ImportReport(BaseModel):
    """What an import actually did — shown to the user afterwards.

    Import is additive: nothing is deleted or overwritten, so every number
    here counts something that was *added* or deliberately *skipped*.
    `documents_restored` counts documents (and, implicitly, a photo) whose
    file bytes were actually recovered — only possible when importing an
    encrypted backup archive (G-36), since a plain JSON export never carries
    `storage_path`/`photo_path` and so always counts every document towards
    `documents_skipped` instead.
    """

    schema_version: int
    people_created: int = 0
    people_skipped: int = 0
    fields_created: int = 0
    relationships_created: int = 0
    relationships_skipped: int = 0
    documents_skipped: int = 0
    documents_restored: int = 0
    sensitive_values_missing: int = 0
    warnings: list[str] = []
