"""Derive plain-English kinship terms from relationship-tree paths (G-31).

A *path* is the BFS step sequence from the tree's center person to a node:
`"up"` walks to a parent, `"down"` to a child, `"sib"` to a sibling,
`"spouse"` to a spouse, `"gup"`/`"gdown"` to a godparent/godchild, and the
social types (`"partner"`, `"friend"`, `"colleague"`, `"custom"`) are only
meaningful as a single terminal step. Pure functions — no DB, no HTTP.
"""

from collections.abc import Iterable

_MALE_ROLES = {"father", "son", "brother", "husband", "godfather", "godson"}
_FEMALE_ROLES = {"mother", "daughter", "sister", "wife", "godmother", "goddaughter"}

_SOCIAL_STEPS = {"partner", "friend", "colleague", "custom"}


def gender_from_roles(roles: Iterable[str]) -> str | None:
    """Infer a person's gender from the roles recorded on their links.

    Args:
        roles (Iterable[str]): Role values (e.g. "mother") attached to the
            person across all of their relationships.

    Returns:
        str | None: "m" or "f" when every gendered role agrees; None when
            no role is gendered or the roles conflict.
    """
    genders = {
        "m" if role in _MALE_ROLES else "f"
        for role in roles
        if role in _MALE_ROLES or role in _FEMALE_ROLES
    }
    return genders.pop() if len(genders) == 1 else None


def _pick(gender: str | None, male: str, female: str, neutral: str) -> str:
    """Choose the gendered variant of a term.

    Args:
        gender (str | None): "m", "f", or None for unknown.
        male (str): Term used when the gender is male.
        female (str): Term used when the gender is female.
        neutral (str): Fallback term when the gender is unknown.

    Returns:
        str: The matching term.
    """
    if gender == "m":
        return male
    if gender == "f":
        return female
    return neutral


def _blood_shape(path: tuple[str, ...]) -> tuple[int, int] | None:
    """Reduce a blood path to its (ups, downs) shape.

    Each `sib` step expands to up-then-down (a sibling is a parent's other
    child), then the whole path must read as ups followed by downs to be a
    recognizable blood line.

    Args:
        path (tuple[str, ...]): Steps containing only "up", "down", "sib".

    Returns:
        tuple[int, int] | None: (ups, downs), or None if the path isn't
            monotonic (e.g. down-then-up is a co-parent, not blood).
    """
    steps: list[str] = []
    for step in path:
        steps.extend(("up", "down") if step == "sib" else (step,))
    if not steps or any(step not in ("up", "down") for step in steps):
        return None
    ups = 0
    while ups < len(steps) and steps[ups] == "up":
        ups += 1
    if any(step != "down" for step in steps[ups:]):
        return None
    return ups, len(steps) - ups


def _blood_term(ups: int, downs: int, gender: str | None) -> str:
    """Name a blood relationship from its (ups, downs) shape.

    Args:
        ups (int): Parent hops at the start of the path.
        downs (int): Child hops at the end of the path.
        gender (str | None): The target person's inferred gender.

    Returns:
        str: A capitalized kinship term ("Great-grandmother", "Cousin", …).
    """
    if downs == 0:
        if ups == 1:
            return _pick(gender, "Father", "Mother", "Parent")
        base = _pick(gender, "grandfather", "grandmother", "grandparent")
        return ("great-" * (ups - 2) + base).capitalize()
    if ups == 0:
        if downs == 1:
            return _pick(gender, "Son", "Daughter", "Child")
        base = _pick(gender, "grandson", "granddaughter", "grandchild")
        return ("great-" * (downs - 2) + base).capitalize()
    if ups == 1 and downs == 1:
        return _pick(gender, "Brother", "Sister", "Sibling")
    if downs == 1:
        base = _pick(gender, "uncle", "aunt", "aunt/uncle")
        return ("great-" * (ups - 2) + base).capitalize()
    if ups == 1:
        base = _pick(gender, "nephew", "niece", "nephew/niece")
        return ("great-" * (downs - 2) + base).capitalize()
    return "Cousin"


def kinship_term(path: tuple[str, ...], gender: str | None) -> str | None:
    """Name a node's relationship to the tree's center person.

    Args:
        path (tuple[str, ...]): BFS steps from the center to the node.
        gender (str | None): The node person's inferred gender ("m"/"f"/None).

    Returns:
        str | None: A caption-ready term ("Mother", "Uncle", "Sister-in-law",
            "Godfather", …), or None when the path has no common name.
    """
    if not path:
        return None
    if path == ("gup",):
        return _pick(gender, "Godfather", "Godmother", "Godparent")
    if path == ("gdown",):
        return _pick(gender, "Godson", "Goddaughter", "Godchild")
    if len(path) == 1 and path[0] in ("partner", "friend", "colleague"):
        return path[0].capitalize()
    if any(step in _SOCIAL_STEPS or step in ("gup", "gdown") for step in path):
        return None
    if path == ("spouse",):
        return _pick(gender, "Husband", "Wife", "Spouse")
    if path.count("spouse") > 1:
        return None
    if path[0] == "spouse":
        # In-law via my spouse: their parent/sibling, or their child (step-).
        shape = _blood_shape(path[1:])
        if shape == (1, 0):
            return _pick(gender, "Father-in-law", "Mother-in-law", "Parent-in-law")
        if shape == (1, 1):
            return _pick(gender, "Brother-in-law", "Sister-in-law", "Sibling-in-law")
        if shape == (0, 1):
            return _pick(gender, "Stepson", "Stepdaughter", "Stepchild")
        return None
    if path[-1] == "spouse":
        # Spouse of a blood relative: step-parent, in-law, or aunt/uncle by marriage.
        shape = _blood_shape(path[:-1])
        if shape == (1, 0):
            return _pick(gender, "Stepfather", "Stepmother", "Stepparent")
        if shape == (1, 1):
            return _pick(gender, "Brother-in-law", "Sister-in-law", "Sibling-in-law")
        if shape == (0, 1):
            return _pick(gender, "Son-in-law", "Daughter-in-law", "Child-in-law")
        if shape == (2, 1):
            return _pick(gender, "Uncle", "Aunt", "Aunt/uncle")
        return None
    if "spouse" in path:
        return None
    shape = _blood_shape(path)
    return _blood_term(*shape, gender) if shape else None
