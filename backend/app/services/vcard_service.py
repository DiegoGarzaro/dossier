"""vCard 4.0 (RFC 6350) export for a person (Phase 3, new idea).

Deliberately simple: no PHOTO embedding and no line-folding for >75-octet
lines (both spec niceties that most modern parsers tolerate skipping).
Sensitive field values are never included (SEC-7) — this file is meant to
leave the app and land in phone/desktop contact books.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import FieldType
from app.core.files import download_filename
from app.models import Person
from app.schemas.relationship import RelationshipOut
from app.services.people_service import PeopleService
from app.services.relationship_service import RelationshipService

# Relationship labels (types and gendered roles, G-31) mapped to RFC 6350
# §6.6.6 RELATED TYPE values; unmapped labels emit RELATED without a TYPE.
_RELATED_TYPE_BY_LABEL = {
    "spouse": "spouse",
    "husband": "spouse",
    "wife": "spouse",
    "partner": "sweetheart",
    "parent": "parent",
    "father": "parent",
    "mother": "parent",
    "child": "child",
    "son": "child",
    "daughter": "child",
    "sibling": "sibling",
    "brother": "sibling",
    "sister": "sibling",
    "friend": "friend",
    "colleague": "colleague",
    "godparent": "kin",
    "godfather": "kin",
    "godmother": "kin",
    "godchild": "kin",
    "godson": "kin",
    "goddaughter": "kin",
}


def _escape(value: str) -> str:
    """Escape a value for a vCard TEXT property (RFC 6350 §3.4).

    Args:
        value (str): The raw value.

    Returns:
        str: The value with backslash, comma, semicolon, and newline escaped.
    """
    return (
        value.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _render(person: Person, relationships: list[RelationshipOut]) -> str:
    """Render a person and their relationships as vCard 4.0 text.

    Args:
        person (Person): The person, with fields loaded.
        relationships (list[RelationshipOut]): The person's resolved relationships.

    Returns:
        str: The complete vCard, CRLF-terminated per line.
    """
    lines = ["BEGIN:VCARD", "VERSION:4.0", f"FN:{_escape(person.full_name)}"]

    given, _, family = person.full_name.rpartition(" ")
    if given:
        lines.append(f"N:{_escape(family)};{_escape(given)};;;")
    else:
        lines.append(f"N:{_escape(person.full_name)};;;;")

    lines.append(f"REV:{person.updated_at.strftime('%Y%m%dT%H%M%SZ')}")
    lines.append(f"UID:urn:dossier:person:{person.id}")

    notes = []
    for field in person.fields:
        if field.type == FieldType.sensitive or not field.value:
            continue
        label = field.label.strip().lower()
        display_value = (
            ("Yes" if field.value == "true" else "No")
            if field.type == FieldType.boolean
            else field.value
        )
        if label == "address":
            lines.append(f"ADR:;;{_escape(field.value)};;;;")
        elif "email" in label:
            lines.append(f"EMAIL:{_escape(field.value)}")
        elif "phone" in label or "mobile" in label or label == "tel":
            lines.append(f"TEL:{_escape(field.value)}")
        else:
            notes.append(f"{field.label}: {display_value}")

    for relationship in relationships:
        related_type = _RELATED_TYPE_BY_LABEL.get(relationship.label.lower())
        type_param = f";TYPE={related_type}" if related_type else ""
        lines.append(f"RELATED{type_param}:{_escape(relationship.person_name)}")

    if notes:
        lines.append(f"NOTE:{_escape(chr(10).join(notes))}")

    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


class VCardService:
    """Builds a vCard export for a person (Phase 3, new idea)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._people = PeopleService(session)
        self._relationships = RelationshipService(session)

    async def build(self, person_id: int) -> tuple[str, str]:
        """Build the vCard text and a safe download filename for a person.

        Args:
            person_id (int): The person id.

        Returns:
            tuple[str, str]: (vcard_text, filename).

        Raises:
            NotFoundError: If the person does not exist.
        """
        person = await self._people.get_detail(person_id)
        relationships = await self._relationships.list_for_person(person_id)
        filename = download_filename(person.full_name, ".vcf", fallback="contact")
        return _render(person, relationships), filename
