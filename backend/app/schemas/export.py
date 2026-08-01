"""JSON export schemas — the portable file format (Phase 3, FR-30 / G3).

The envelope is versioned so a future import can recognize what it is
reading. Bump `EXPORT_SCHEMA_VERSION` whenever the shape changes in a way
an importer must react to.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import FieldType, RelationshipType

EXPORT_SCHEMA_VERSION = 1

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
    volume and are covered by the directory backup (G1/G2). The on-disk
    storage filename is deliberately excluded (SEC-6).
    """

    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class ExportPerson(BaseModel):
    """One person with their fields and document metadata."""

    id: int
    full_name: str = Field(min_length=1, max_length=255)
    has_photo: bool
    created_at: datetime
    updated_at: datetime
    fields: list[ExportField]
    documents: list[ExportDocument]


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
    """

    schema_version: int
    people_created: int = 0
    people_skipped: int = 0
    fields_created: int = 0
    relationships_created: int = 0
    relationships_skipped: int = 0
    documents_skipped: int = 0
    sensitive_values_missing: int = 0
    warnings: list[str] = []
