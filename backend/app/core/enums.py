"""Shared domain enums."""

from enum import StrEnum


class FieldType(StrEnum):
    """Supported custom field types (FR-13)."""

    text = "text"
    textarea = "textarea"
    number = "number"
    date = "date"
    boolean = "boolean"
    sensitive = "sensitive"


class RelationshipType(StrEnum):
    """Supported relationship types (FR-22, Phase 2)."""

    spouse = "spouse"
    parent = "parent"
    child = "child"
    sibling = "sibling"
    custom = "custom"
