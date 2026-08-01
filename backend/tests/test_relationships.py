"""Relationship flow tests: canonicalization, inverse labels, validation (Epic E)."""

from httpx import AsyncClient


async def _create_person(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def test_spouse_relationship_symmetric_label(authed_client: AsyncClient) -> None:
    """Spouse is symmetric: both sides see the same label (FR-22/23)."""
    alice = await _create_person(authed_client, "Alice Spouse")
    bob = await _create_person(authed_client, "Bob Spouse")

    created = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "spouse"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["person_id"] == bob["id"]
    assert body["label"] == "Spouse"

    alice_detail = (await authed_client.get(f"/api/people/{alice['id']}")).json()
    bob_detail = (await authed_client.get(f"/api/people/{bob['id']}")).json()
    assert [r["label"] for r in alice_detail["relationships"]] == ["Spouse"]
    assert alice_detail["relationships"][0]["person_id"] == bob["id"]
    assert [r["label"] for r in bob_detail["relationships"]] == ["Spouse"]
    assert bob_detail["relationships"][0]["person_id"] == alice["id"]

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_parent_child_inverse_label_and_canonicalization(authed_client: AsyncClient) -> None:
    """parent/child canonicalize to one stored row with correct inverse labels (FR-23)."""
    parent = await _create_person(authed_client, "Parent Person")
    child = await _create_person(authed_client, "Child Person")

    # From the parent's card: "child is my child".
    created = await authed_client.post(
        "/api/relationships",
        json={"person_id": parent["id"], "related_person_id": child["id"], "type": "child"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Child"

    parent_detail = (await authed_client.get(f"/api/people/{parent['id']}")).json()
    child_detail = (await authed_client.get(f"/api/people/{child['id']}")).json()
    assert parent_detail["relationships"][0]["label"] == "Child"
    assert parent_detail["relationships"][0]["person_id"] == child["id"]
    assert child_detail["relationships"][0]["label"] == "Parent"
    assert child_detail["relationships"][0]["person_id"] == parent["id"]

    for person in (parent, child):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_parent_type_from_child_side_is_equivalent(authed_client: AsyncClient) -> None:
    """Selecting type=parent from the child's card canonicalizes identically to type=child."""
    parent = await _create_person(authed_client, "Parent Person Two")
    child = await _create_person(authed_client, "Child Person Two")

    # From the child's card: "parent is my parent".
    created = await authed_client.post(
        "/api/relationships",
        json={"person_id": child["id"], "related_person_id": parent["id"], "type": "parent"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Parent"

    parent_detail = (await authed_client.get(f"/api/people/{parent['id']}")).json()
    assert parent_detail["relationships"][0]["label"] == "Child"

    for person in (parent, child):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_self_link_rejected(authed_client: AsyncClient) -> None:
    """A person can't be related to themselves (FR-24)."""
    person = await _create_person(authed_client, "Solo Person")
    response = await authed_client.post(
        "/api/relationships",
        json={"person_id": person["id"], "related_person_id": person["id"], "type": "sibling"},
    )
    assert response.status_code == 400
    await authed_client.delete(f"/api/people/{person['id']}")


async def test_duplicate_link_rejected_both_orders(authed_client: AsyncClient) -> None:
    """Exact duplicates are rejected, including the reversed order for symmetric types (FR-24)."""
    alice = await _create_person(authed_client, "Alice Sibling")
    bob = await _create_person(authed_client, "Bob Sibling")

    first = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "sibling"},
    )
    assert first.status_code == 201

    exact_dup = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "sibling"},
    )
    assert exact_dup.status_code == 409

    reversed_dup = await authed_client.post(
        "/api/relationships",
        json={"person_id": bob["id"], "related_person_id": alice["id"], "type": "sibling"},
    )
    assert reversed_dup.status_code == 409

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_custom_relationship_requires_label_and_mirrors(authed_client: AsyncClient) -> None:
    """Custom type needs a label and shows the same text on both sides (FR-22/23)."""
    alice = await _create_person(authed_client, "Alice Custom")
    bob = await _create_person(authed_client, "Bob Custom")

    missing_label = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "custom"},
    )
    assert missing_label.status_code == 400

    created = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": alice["id"],
            "related_person_id": bob["id"],
            "type": "custom",
            "custom_label": "Godmother",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Godmother"

    bob_detail = (await authed_client.get(f"/api/people/{bob['id']}")).json()
    assert bob_detail["relationships"][0]["label"] == "Godmother"

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_related_person_not_found(authed_client: AsyncClient) -> None:
    """Linking to a nonexistent person 404s (edge case around FR-22)."""
    alice = await _create_person(authed_client, "Alice Alone")
    response = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": 999_999, "type": "spouse"},
    )
    assert response.status_code == 404
    await authed_client.delete(f"/api/people/{alice['id']}")


async def test_role_specific_label_with_generic_inverse(authed_client: AsyncClient) -> None:
    """A gendered role (Mother) labels the counterpart; the unknown side stays generic (G-31)."""
    mom = await _create_person(authed_client, "Maria Role")
    kid = await _create_person(authed_client, "Kid Role")

    # From the kid's card: "Maria is my mother".
    created = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": kid["id"],
            "related_person_id": mom["id"],
            "type": "parent",
            "related_role": "mother",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Mother"

    kid_detail = (await authed_client.get(f"/api/people/{kid['id']}")).json()
    mom_detail = (await authed_client.get(f"/api/people/{mom['id']}")).json()
    assert kid_detail["relationships"][0]["label"] == "Mother"
    # The kid's own role was never stated, so the mother sees the generic label.
    assert mom_detail["relationships"][0]["label"] == "Child"

    for person in (mom, kid):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_role_must_match_type(authed_client: AsyncClient) -> None:
    """A role that contradicts the chosen type is rejected (G-31)."""
    alice = await _create_person(authed_client, "Alice Mismatch")
    bob = await _create_person(authed_client, "Bob Mismatch")

    response = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": alice["id"],
            "related_person_id": bob["id"],
            "type": "spouse",
            "related_role": "mother",
        },
    )
    assert response.status_code == 400

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_godchild_canonicalizes_to_godparent(authed_client: AsyncClient) -> None:
    """godchild stores as a godparent row; the reverse duplicate is caught (G-31)."""
    godmother = await _create_person(authed_client, "Godmother Canon")
    kid = await _create_person(authed_client, "Godkid Canon")

    # From the godmother's card: "kid is my goddaughter".
    created = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": godmother["id"],
            "related_person_id": kid["id"],
            "type": "godchild",
            "related_role": "goddaughter",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Goddaughter"

    kid_detail = (await authed_client.get(f"/api/people/{kid['id']}")).json()
    assert kid_detail["relationships"][0]["label"] == "Godparent"

    # Linking again from the kid's side is the same stored relationship.
    duplicate = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": kid["id"],
            "related_person_id": godmother["id"],
            "type": "godparent",
        },
    )
    assert duplicate.status_code == 409

    for person in (godmother, kid):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_friend_relationship_symmetric(authed_client: AsyncClient) -> None:
    """New social categories (friend) are symmetric like spouse (G-31)."""
    alice = await _create_person(authed_client, "Alice Friend")
    bob = await _create_person(authed_client, "Bob Friend")

    created = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "friend"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["label"] == "Friend"

    bob_detail = (await authed_client.get(f"/api/people/{bob['id']}")).json()
    assert bob_detail["relationships"][0]["label"] == "Friend"

    reversed_dup = await authed_client.post(
        "/api/relationships",
        json={"person_id": bob["id"], "related_person_id": alice["id"], "type": "friend"},
    )
    assert reversed_dup.status_code == 409

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_remove_relationship_from_either_side(authed_client: AsyncClient) -> None:
    """Deleting a relationship removes it from both people's records (FR-25)."""
    alice = await _create_person(authed_client, "Alice Remove")
    bob = await _create_person(authed_client, "Bob Remove")

    created = await authed_client.post(
        "/api/relationships",
        json={"person_id": alice["id"], "related_person_id": bob["id"], "type": "spouse"},
    )
    relationship_id = created.json()["id"]

    assert (await authed_client.delete(f"/api/relationships/{relationship_id}")).status_code == 204

    alice_detail = (await authed_client.get(f"/api/people/{alice['id']}")).json()
    bob_detail = (await authed_client.get(f"/api/people/{bob['id']}")).json()
    assert alice_detail["relationships"] == []
    assert bob_detail["relationships"] == []

    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")
