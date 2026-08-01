"""Relationship tree endpoint tests (Phase 2b)."""

from httpx import AsyncClient


async def _create_person(client: AsyncClient, name: str) -> int:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _link(client: AsyncClient, person_id: int, related_id: int, type_: str, **extra) -> None:
    response = await client.post(
        "/api/relationships",
        json={"person_id": person_id, "related_person_id": related_id, "type": type_, **extra},
    )
    assert response.status_code == 201, response.text


async def test_tree_generations_and_edges(authed_client: AsyncClient) -> None:
    """A three-generation family resolves to correct relative generations (Phase 2b)."""
    grandma = await _create_person(authed_client, "Grandma Tree")
    dad = await _create_person(authed_client, "Dad Tree")
    mom = await _create_person(authed_client, "Mom Tree")
    kid = await _create_person(authed_client, "Kid Tree")

    await _link(authed_client, dad, grandma, "parent")  # grandma is dad's parent
    await _link(authed_client, dad, mom, "spouse")
    await _link(authed_client, dad, kid, "child")  # kid is dad's child

    tree = (await authed_client.get(f"/api/people/{dad}/tree")).json()
    assert tree["center_id"] == dad
    generations = {node["id"]: node["generation"] for node in tree["nodes"]}
    assert generations[dad] == 0
    assert generations[mom] == 0  # spouse is a peer
    assert generations[grandma] == -1
    assert generations[kid] == 1

    kinds = sorted(edge["type"] for edge in tree["edges"])
    assert kinds == ["parent", "parent", "spouse"]

    # The graph is connected: viewing from the kid shifts everyone one generation up.
    kid_tree = (await authed_client.get(f"/api/people/{kid}/tree")).json()
    kid_generations = {node["id"]: node["generation"] for node in kid_tree["nodes"]}
    assert kid_generations[kid] == 0
    assert kid_generations[dad] == -1
    assert kid_generations[grandma] == -2

    for pid in (grandma, dad, mom, kid):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_sibling_and_custom_are_peers(authed_client: AsyncClient) -> None:
    """Sibling and custom links keep both people in the same generation."""
    ana = await _create_person(authed_client, "Ana Peer")
    rui = await _create_person(authed_client, "Rui Peer")
    god = await _create_person(authed_client, "Godmother Peer")

    await _link(authed_client, ana, rui, "sibling")
    await _link(authed_client, ana, god, "custom", custom_label="Godmother")

    tree = (await authed_client.get(f"/api/people/{ana}/tree")).json()
    generations = {node["id"]: node["generation"] for node in tree["nodes"]}
    assert generations == {ana: 0, rui: 0, god: 0}
    custom_edge = next(edge for edge in tree["edges"] if edge["type"] == "custom")
    assert custom_edge["label"] == "Godmother"

    for pid in (ana, rui, god):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_kinship_captions(authed_client: AsyncClient) -> None:
    """Nodes carry derived kinship terms relative to the center person (G-31)."""
    kid = await _create_person(authed_client, "Kid Kin")
    dad = await _create_person(authed_client, "Dad Kin")
    mom = await _create_person(authed_client, "Mom Kin")
    grandma = await _create_person(authed_client, "Grandma Kin")
    uncle = await _create_person(authed_client, "Uncle Kin")
    cousin = await _create_person(authed_client, "Cousin Kin")

    await _link(authed_client, kid, dad, "parent", related_role="father")
    await _link(authed_client, kid, mom, "parent", related_role="mother")
    await _link(authed_client, dad, grandma, "parent", related_role="mother")
    await _link(authed_client, dad, uncle, "sibling", related_role="brother")
    await _link(authed_client, uncle, cousin, "child")

    tree = (await authed_client.get(f"/api/people/{kid}/tree")).json()
    kinship = {node["id"]: node["kinship"] for node in tree["nodes"]}
    assert kinship[kid] is None
    assert kinship[dad] == "Father"
    assert kinship[mom] == "Mother"
    assert kinship[grandma] == "Grandmother"
    assert kinship[uncle] == "Uncle"
    assert kinship[cousin] == "Cousin"

    for pid in (kid, dad, mom, grandma, uncle, cousin):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_inlaw_kinship(authed_client: AsyncClient) -> None:
    """A spouse's parent resolves to an in-law term (G-31)."""
    hub = await _create_person(authed_client, "Hub Inlaw")
    wife = await _create_person(authed_client, "Wife Inlaw")
    wifes_mom = await _create_person(authed_client, "WifesMom Inlaw")

    await _link(authed_client, hub, wife, "spouse", related_role="wife")
    await _link(authed_client, wife, wifes_mom, "parent", related_role="mother")

    tree = (await authed_client.get(f"/api/people/{hub}/tree")).json()
    kinship = {node["id"]: node["kinship"] for node in tree["nodes"]}
    assert kinship[wife] == "Wife"
    assert kinship[wifes_mom] == "Mother-in-law"

    for pid in (hub, wife, wifes_mom):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_godparent_is_older_generation(authed_client: AsyncClient) -> None:
    """Godparents sit one generation above, with a gendered caption (G-31)."""
    kid = await _create_person(authed_client, "Kid God")
    godmother = await _create_person(authed_client, "Godmother God")

    await _link(authed_client, kid, godmother, "godparent", related_role="godmother")

    tree = (await authed_client.get(f"/api/people/{kid}/tree")).json()
    nodes = {node["id"]: node for node in tree["nodes"]}
    assert nodes[godmother]["generation"] == -1
    assert nodes[godmother]["kinship"] == "Godmother"

    for pid in (kid, godmother):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_blood_generation_wins_over_godparent_shortcut(
    authed_client: AsyncClient,
) -> None:
    """A grandparent who is also a godparent stays at the blood generation (G-32).

    Structural (blood/marriage) edges define the generation ladder; a
    godparent shortcut must not pull an ancestor up out of their real
    generation, and the caption should reflect the blood tie.
    """
    kid = await _create_person(authed_client, "Kid Ladder")
    dad = await _create_person(authed_client, "Dad Ladder")
    grandpa = await _create_person(authed_client, "Grandpa Ladder")

    await _link(authed_client, kid, dad, "parent", related_role="father")
    await _link(authed_client, dad, grandpa, "parent", related_role="father")
    # The same grandpa is also the kid's godfather (one-hop godparent shortcut).
    await _link(authed_client, kid, grandpa, "godparent", related_role="godfather")

    tree = (await authed_client.get(f"/api/people/{kid}/tree")).json()
    nodes = {node["id"]: node for node in tree["nodes"]}
    assert nodes[grandpa]["generation"] == -2  # blood grandfather, not gen -1
    assert nodes[grandpa]["kinship"] == "Grandfather"

    for pid in (kid, dad, grandpa):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_generations_stable_across_viewers(authed_client: AsyncClient) -> None:
    """The generation gap between any two people is the same from either view (G-32).

    Viewing the tree from different people only shifts the origin; the
    relative structure (in-laws one row up, grandparents two rows up) must
    be identical no matter who is centered.
    """
    kid = await _create_person(authed_client, "Kid Stable")
    dad = await _create_person(authed_client, "Dad Stable")
    mom = await _create_person(authed_client, "Mom Stable")
    grandpa = await _create_person(authed_client, "Grandpa Stable")

    await _link(authed_client, kid, dad, "parent", related_role="father")
    await _link(authed_client, kid, mom, "parent", related_role="mother")
    await _link(authed_client, dad, mom, "spouse", related_role="wife")
    await _link(authed_client, dad, grandpa, "parent", related_role="father")
    # Grandpa is also the kid's godfather — the cross-generation shortcut.
    await _link(authed_client, kid, grandpa, "godparent", related_role="godfather")

    def gens(payload: dict) -> dict[int, int]:
        return {node["id"]: node["generation"] for node in payload["nodes"]}

    from_mom = gens((await authed_client.get(f"/api/people/{mom}/tree")).json())
    from_dad = gens((await authed_client.get(f"/api/people/{dad}/tree")).json())

    # Grandpa is dad's father: exactly one generation above dad in both views.
    assert from_dad[grandpa] - from_dad[dad] == -1
    assert from_mom[grandpa] - from_mom[dad] == -1
    # Mom and dad are spouses: same generation from either viewpoint.
    assert from_mom[dad] == from_mom[mom]
    assert from_dad[dad] == from_dad[mom]

    for pid in (kid, dad, mom, grandpa):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_person_without_relationships(authed_client: AsyncClient) -> None:
    """A person with no links yields a single-node tree with no edges."""
    solo = await _create_person(authed_client, "Solo Tree")
    tree = (await authed_client.get(f"/api/people/{solo}/tree")).json()
    assert [node["id"] for node in tree["nodes"]] == [solo]
    assert tree["edges"] == []
    await authed_client.delete(f"/api/people/{solo}")


async def test_tree_excludes_unconnected_people(authed_client: AsyncClient) -> None:
    """People outside the center's connected component don't appear."""
    ana = await _create_person(authed_client, "Ana Island")
    rui = await _create_person(authed_client, "Rui Island")
    stranger = await _create_person(authed_client, "Stranger Island")
    await _link(authed_client, ana, rui, "spouse")

    tree = (await authed_client.get(f"/api/people/{ana}/tree")).json()
    ids = {node["id"] for node in tree["nodes"]}
    assert ids == {ana, rui}
    assert stranger not in ids

    for pid in (ana, rui, stranger):
        await authed_client.delete(f"/api/people/{pid}")


async def test_tree_not_found(authed_client: AsyncClient) -> None:
    """An unknown person 404s."""
    assert (await authed_client.get("/api/people/999999/tree")).status_code == 404
