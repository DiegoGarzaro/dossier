"""JSON import / restore-from-export (Phase 3, FR-30 / G3).

**Import is additive and never destructive.** It only ever creates records:
nothing existing is deleted, renamed, or overwritten. A person whose name is
already on file is skipped, and links from the file are reconnected to that
existing record instead — which makes re-running the same file a no-op rather
than a way to duplicate a vault.

Two things in an export can't be restored and are reported instead of failing:
document *bytes* (the file only carries metadata; the blobs live on `/data`)
and `sensitive` values withheld by a default export (SEC-7).
"""

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RelationshipType
from app.core.errors import AppError, InvalidInputError
from app.models import Person, PersonField
from app.repositories.people_repo import PeopleRepository
from app.schemas.export import (
    EXPORT_SCHEMA_VERSION,
    ExportEnvelope,
    ExportPerson,
    ExportRelationship,
    ImportReport,
)
from app.schemas.relationship import RelationshipCreate
from app.services.field_service import validate_value
from app.services.relationship_service import RelationshipService
from app.services.tag_service import TagService

# A person-scoped export can reference someone who isn't in the file; refuse
# absurd sizes before doing any work rather than importing for minutes.
MAX_IMPORT_PEOPLE = 10_000

# Directional types store the older side as person_a. Recreating a link where
# the *younger* side carries the role means asking for the alias instead.
_ALIAS_OF_CANONICAL = {
    RelationshipType.parent: RelationshipType.child,
    RelationshipType.godparent: RelationshipType.godchild,
}


class ImportService:
    """Applies an export envelope to the vault, additively (FR-30 / G3)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._people = PeopleRepository(session)
        self._relationships = RelationshipService(session)
        self._tags = TagService(session)

    async def apply(self, envelope: ExportEnvelope) -> ImportReport:
        """Import an export envelope, creating what's missing and reporting the rest.

        Args:
            envelope (ExportEnvelope): The parsed export file.

        Returns:
            ImportReport: Counts of what was created and skipped, plus warnings.

        Raises:
            InvalidInputError: The file isn't a Dossier export, was produced by a
                newer schema version, is too large, or carries a field value that
                fails its type's validation (FR-14). Nothing is written in that
                case — the request's transaction rolls back as a whole.
        """
        self._check_envelope(envelope)
        report = ImportReport(schema_version=envelope.schema_version)

        # Validate every value before writing anything, so a bad file is
        # rejected outright instead of applying half of itself.
        for exported in envelope.people:
            for field in exported.fields:
                validate_value(field.type, field.value)

        id_map: dict[int, int] = {}
        for exported in envelope.people:
            report.documents_skipped += len(exported.documents)
            report.sensitive_values_missing += sum(
                1 for field in exported.fields if field.value_omitted
            )
            existing = await self._people.get_by_name(exported.full_name)
            if existing is not None:
                id_map[exported.id] = existing.id
                report.people_skipped += 1
                report.warnings.append(
                    f'Person "{exported.full_name}" already exists — skipped, and any links '
                    "in the file were reconnected to the existing record."
                )
                continue
            person = await self._create_person(exported)
            id_map[exported.id] = person.id
            report.people_created += 1
            report.fields_created += len(person.fields)

        for link in envelope.relationships:
            await self._restore_link(link, id_map, report)

        if report.documents_skipped:
            report.warnings.append(
                f"{report.documents_skipped} document(s) were listed in the file but not "
                "restored — an export carries document metadata, never the files themselves. "
                "Restore those from the /data volume backup."
            )
        if report.sensitive_values_missing:
            report.warnings.append(
                f"{report.sensitive_values_missing} sensitive value(s) were withheld when this "
                "file was exported, so those fields came back empty."
            )
        return report

    def _check_envelope(self, envelope: ExportEnvelope) -> None:
        """Reject files this build can't safely interpret.

        Args:
            envelope (ExportEnvelope): The parsed export file.

        Returns:
            None

        Raises:
            InvalidInputError: Foreign generator, unsupported version, or too large.
        """
        if envelope.generator != "dossier":
            raise InvalidInputError("This file wasn't produced by Dossier")
        if envelope.schema_version > EXPORT_SCHEMA_VERSION:
            raise InvalidInputError(
                "This file was produced by a newer version of Dossier and can't be imported"
            )
        if envelope.schema_version < 1:
            raise InvalidInputError("This file has an invalid schema version")
        if len(envelope.people) > MAX_IMPORT_PEOPLE:
            raise InvalidInputError(
                f"This file holds more than {MAX_IMPORT_PEOPLE} people and was refused"
            )

    async def _create_person(self, exported: ExportPerson) -> Person:
        """Create a person with exactly the fields, favorite flag, and tags in the file.

        The seeded system fields are deliberately *not* added here: the export
        already carries them, so letting `PeopleService.create` seed would
        duplicate every built-in field. Tags are find-or-created by name and
        assigned only to newly created people — a skipped (already-existing)
        person never has their tags touched, keeping import additive.

        Args:
            exported (ExportPerson): The person as exported.

        Returns:
            Person: The persisted person with its fields.
        """
        ordered = sorted(exported.fields, key=lambda field: field.position)
        person = Person(full_name=exported.full_name, is_favorite=exported.is_favorite)
        person.fields = [
            PersonField(
                label=field.label,
                value=field.value,
                type=field.type,
                is_pinned=field.is_pinned,
                is_system=field.is_system,
                position=position,
            )
            for position, field in enumerate(ordered)
        ]
        person = await self._people.add(person)
        for tag_name in exported.tags:
            await self._tags.assign(person.id, tag_name)
        return person

    async def _restore_link(
        self, link: ExportRelationship, id_map: dict[int, int], report: ImportReport
    ) -> None:
        """Recreate one relationship, resolving both sides to real people.

        Sides are resolved through the file's id map first, then by exact name
        against people already on file — so a person-scoped export still links
        up to relatives who were already in the vault.

        Args:
            link (ExportRelationship): The exported link.
            id_map (dict[int, int]): File person id -> database person id.
            report (ImportReport): Mutated with the outcome.

        Returns:
            None
        """
        person_a = await self._resolve(link.person_a_id, link.person_a_name, id_map)
        person_b = await self._resolve(link.person_b_id, link.person_b_name, id_map)
        if person_a is None or person_b is None:
            missing = link.person_a_name if person_a is None else link.person_b_name
            report.relationships_skipped += 1
            report.warnings.append(
                f'Skipped a "{link.type}" link because "{missing}" is not in this file '
                "and not already on file."
            )
            return

        # The role always describes the *related* person, so whichever side
        # carries one becomes the target of the create call.
        if link.role_a:
            viewer, related, role = person_b, person_a, link.role_a
        else:
            viewer, related, role = person_a, person_b, link.role_b
        type_ = link.type
        if related == person_b and type_ in _ALIAS_OF_CANONICAL:
            # "person_b is my child" rather than "person_a is my parent".
            type_ = _ALIAS_OF_CANONICAL[type_]

        try:
            await self._relationships.create(
                RelationshipCreate(
                    person_id=viewer,
                    related_person_id=related,
                    type=type_,
                    related_role=role,
                    custom_label=link.custom_label,
                )
            )
        except (AppError, ValidationError) as error:
            # Duplicates are expected on re-import; anything else is a quirk of
            # the file, not a reason to abandon everything already imported.
            report.relationships_skipped += 1
            if not isinstance(error, AppError) or error.status != 409:
                report.warnings.append(
                    f'Skipped a "{link.type}" link between "{link.person_a_name}" and '
                    f'"{link.person_b_name}": {error}'
                )
            return
        report.relationships_created += 1

    async def _resolve(
        self, exported_id: int, name: str, id_map: dict[int, int]
    ) -> int | None:
        """Map an exported person id to a real one, falling back to an exact name match.

        Args:
            exported_id (int): The person id as written in the file.
            name (str): The person's name as written in the file.
            id_map (dict[int, int]): File person id -> database person id.

        Returns:
            int | None: The database person id, or None when unresolvable.
        """
        if exported_id in id_map:
            return id_map[exported_id]
        existing = await self._people.get_by_name(name)
        return existing.id if existing else None
