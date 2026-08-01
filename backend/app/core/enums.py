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
    """Supported relationship types (FR-22, Phase 2; extended in G-31).

    `child` and `godchild` are creation-time aliases only: they are
    canonicalized to a `parent`/`godparent` row with the two people swapped
    and are never stored (Architecture §4.2).
    """

    spouse = "spouse"
    partner = "partner"
    parent = "parent"
    child = "child"
    sibling = "sibling"
    friend = "friend"
    colleague = "colleague"
    godparent = "godparent"
    godchild = "godchild"
    custom = "custom"


class RelationshipRole(StrEnum):
    """Optional gendered role for the *related* person on a link (G-31).

    A role refines its structural type — e.g. `mother` refines `parent` —
    and drives labels like "Mother" on cards and gendered kinship captions
    ("Grandmother of X") in the tree.
    """

    father = "father"
    mother = "mother"
    son = "son"
    daughter = "daughter"
    brother = "brother"
    sister = "sister"
    husband = "husband"
    wife = "wife"
    godfather = "godfather"
    godmother = "godmother"
    godson = "godson"
    goddaughter = "goddaughter"
