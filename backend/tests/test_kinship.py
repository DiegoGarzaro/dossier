"""Unit tests for kinship term derivation (G-31). Pure functions, no DB."""

from app.services.kinship import gender_from_roles, kinship_term


def test_ancestor_ladder_terms() -> None:
    """Parent chains produce (great-)grandparent terms, gendered when known."""
    assert kinship_term(("up",), "f") == "Mother"
    assert kinship_term(("up", "up"), "m") == "Grandfather"
    assert kinship_term(("up", "up", "up"), "f") == "Great-grandmother"
    assert kinship_term(("up", "up", "up", "up"), None) == "Great-great-grandparent"


def test_descendant_ladder_terms() -> None:
    """Child chains mirror the ancestor ladder."""
    assert kinship_term(("down",), "m") == "Son"
    assert kinship_term(("down", "down"), "f") == "Granddaughter"
    assert kinship_term(("down", "down", "down"), None) == "Great-grandchild"


def test_sibling_direct_and_via_shared_parent() -> None:
    """A sibling edge and an up-then-down hop both resolve to Sibling."""
    assert kinship_term(("sib",), "f") == "Sister"
    assert kinship_term(("up", "down"), None) == "Sibling"


def test_collateral_terms() -> None:
    """Aunt/uncle, nephew/niece, and cousin patterns resolve."""
    assert kinship_term(("up", "sib"), "m") == "Uncle"
    assert kinship_term(("up", "up", "sib"), "f") == "Great-aunt"
    assert kinship_term(("sib", "down"), "f") == "Niece"
    assert kinship_term(("sib", "down"), None) == "Nephew/niece"
    assert kinship_term(("up", "sib", "down"), "m") == "Cousin"


def test_inlaw_and_step_terms() -> None:
    """One spouse hop at either end produces in-law and step terms."""
    assert kinship_term(("spouse",), "f") == "Wife"
    assert kinship_term(("spouse", "up"), "f") == "Mother-in-law"
    assert kinship_term(("spouse", "sib"), "m") == "Brother-in-law"
    assert kinship_term(("spouse", "down"), "m") == "Stepson"
    assert kinship_term(("up", "spouse"), "m") == "Stepfather"
    assert kinship_term(("sib", "spouse"), "f") == "Sister-in-law"
    assert kinship_term(("down", "spouse"), "f") == "Daughter-in-law"


def test_social_and_god_steps() -> None:
    """Single social/god steps resolve; anything past them does not."""
    assert kinship_term(("friend",), None) == "Friend"
    assert kinship_term(("colleague",), None) == "Colleague"
    assert kinship_term(("partner",), None) == "Partner"
    assert kinship_term(("gup",), "f") == "Godmother"
    assert kinship_term(("gdown",), None) == "Godchild"
    assert kinship_term(("friend", "up"), None) is None
    assert kinship_term(("gup", "up"), None) is None


def test_unmatched_patterns_return_none() -> None:
    """Paths that aren't a recognizable kinship shape yield no caption."""
    assert kinship_term((), None) is None
    assert kinship_term(("down", "up"), None) is None  # co-parent, not blood
    assert kinship_term(("spouse", "spouse"), None) is None
    assert kinship_term(("spouse", "up", "spouse"), None) is None
    assert kinship_term(("custom",), None) is None  # edge pill already shows the label


def test_gender_from_roles() -> None:
    """Roles imply a gender only when they all agree."""
    assert gender_from_roles(["mother", "sister"]) == "f"
    assert gender_from_roles(["father"]) == "m"
    assert gender_from_roles([]) is None
    assert gender_from_roles(["mother", "father"]) is None
