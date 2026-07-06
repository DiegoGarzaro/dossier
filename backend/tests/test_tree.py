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
