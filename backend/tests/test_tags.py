"""Tag + favorite tests: CRUD, assignment, index filtering (Phase 2, "Organizing people")."""

from httpx import AsyncClient


async def _create_person(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def _create_tag(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/tags", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def test_tag_routes_require_authentication(client: AsyncClient) -> None:
    """Every tag route and the person-tag routes sit behind the auth guard (SEC-1)."""
    assert (await client.get("/api/tags")).status_code == 401

    # State-changing methods need a valid CSRF header to get past the CSRF
    # middleware and reach the auth guard at all (SEC-3), same as test_import.py.
    await client.get("/api/auth/status")  # seeds the CSRF cookie
    client.headers["x-csrf-token"] = client.cookies["dossier_csrf"]

    assert (await client.post("/api/tags", json={"name": "x"})).status_code == 401
    assert (await client.patch("/api/tags/1", json={"name": "x"})).status_code == 401
    assert (await client.delete("/api/tags/1")).status_code == 401
    assert (await client.post("/api/people/1/tags", json={"name": "x"})).status_code == 401
    assert (await client.delete("/api/people/1/tags/1")).status_code == 401


async def test_tag_create_list_rename_delete(authed_client: AsyncClient) -> None:
    """Basic tag CRUD: a fresh tag has a zero person_count and disappears on delete."""
    tag = await _create_tag(authed_client, "Family")
    assert tag["name"] == "Family"
    assert tag["person_count"] == 0

    listing = (await authed_client.get("/api/tags")).json()
    assert any(t["id"] == tag["id"] for t in listing)

    renamed = await authed_client.patch(f"/api/tags/{tag['id']}", json={"name": "Close Family"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Close Family"

    assert (await authed_client.delete(f"/api/tags/{tag['id']}")).status_code == 204
    listing_after = (await authed_client.get("/api/tags")).json()
    assert all(t["id"] != tag["id"] for t in listing_after)


async def test_tag_name_is_normalized_on_create_and_rename(authed_client: AsyncClient) -> None:
    """Internal whitespace collapses and edges trim ("  Close   Family " -> "Close Family")."""
    tag = await _create_tag(authed_client, "  Close   Family ")
    assert tag["name"] == "Close Family"

    other = await _create_tag(authed_client, "Renameable")
    renamed = await authed_client.patch(
        f"/api/tags/{other['id']}", json={"name": "  Odd   Spacing  "}
    )
    assert renamed.json()["name"] == "Odd Spacing"

    await authed_client.delete(f"/api/tags/{tag['id']}")
    await authed_client.delete(f"/api/tags/{other['id']}")


async def test_tag_duplicate_name_differing_only_in_case_conflicts(
    authed_client: AsyncClient,
) -> None:
    """Creating (or renaming to) a name that differs only in case is a 409."""
    tag = await _create_tag(authed_client, "Friends")
    dup = await authed_client.post("/api/tags", json={"name": "friends"})
    assert dup.status_code == 409

    other = await _create_tag(authed_client, "Colleagues")
    rename_dup = await authed_client.patch(f"/api/tags/{other['id']}", json={"name": "FRIENDS"})
    assert rename_dup.status_code == 409
    # Renaming a tag to its own (differently-cased) name is not a conflict with itself.
    rename_self = await authed_client.patch(f"/api/tags/{tag['id']}", json={"name": "FRIENDS"})
    assert rename_self.status_code == 200

    await authed_client.delete(f"/api/tags/{tag['id']}")
    await authed_client.delete(f"/api/tags/{other['id']}")


async def test_tag_rename_and_delete_unknown_id_404(authed_client: AsyncClient) -> None:
    """Renaming or deleting a tag id that doesn't exist is a clean 404."""
    assert (
        await authed_client.patch("/api/tags/999999", json={"name": "Nope"})
    ).status_code == 404
    assert (await authed_client.delete("/api/tags/999999")).status_code == 404


async def test_assign_tag_to_person_is_idempotent(authed_client: AsyncClient) -> None:
    """Assigning attaches the tag; assigning the same name again is a no-op, not an error."""
    person = await _create_person(authed_client, "Tag Assignee")
    pid = person["id"]

    first = await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Family"})
    assert first.status_code == 201, first.text
    tag = first.json()
    assert tag["person_count"] == 1

    second = await authed_client.post(f"/api/people/{pid}/tags", json={"name": "family"})
    assert second.status_code == 201
    assert second.json()["id"] == tag["id"]  # matched case-insensitively, same tag
    assert second.json()["person_count"] == 1  # not double-counted

    detail = (await authed_client.get(f"/api/people/{pid}")).json()
    assert [t["name"] for t in detail["tags"]] == ["Family"]  # not duplicated on the person

    await authed_client.delete(f"/api/people/{pid}")
    await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_assign_creates_a_brand_new_tag_on_type(authed_client: AsyncClient) -> None:
    """Posting a name with no existing tag creates it, then assigns it (create-on-type)."""
    person = await _create_person(authed_client, "Create On Type")
    pid = person["id"]

    response = await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Brand New"})
    assert response.status_code == 201, response.text
    tag = response.json()

    all_tags = (await authed_client.get("/api/tags")).json()
    assert any(t["id"] == tag["id"] and t["name"] == "Brand New" for t in all_tags)

    await authed_client.delete(f"/api/people/{pid}")
    await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_assign_to_unknown_person_404(authed_client: AsyncClient) -> None:
    """Assigning a tag to a nonexistent person is a 404, not a stray tag."""
    response = await authed_client.post("/api/people/999999/tags", json={"name": "Ghost"})
    assert response.status_code == 404
    all_tags = (await authed_client.get("/api/tags")).json()
    assert all(t["name"] != "Ghost" for t in all_tags)


async def test_unassign_removes_link_but_keeps_tag_and_person(authed_client: AsyncClient) -> None:
    """Unassigning drops the link only: both the tag and the person survive."""
    person = await _create_person(authed_client, "Unassign Target")
    pid = person["id"]
    tag = (await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Temp"})).json()

    unassigned = await authed_client.delete(f"/api/people/{pid}/tags/{tag['id']}")
    assert unassigned.status_code == 204

    detail = (await authed_client.get(f"/api/people/{pid}"))
    assert detail.status_code == 200
    assert detail.json()["tags"] == []

    tags = (await authed_client.get("/api/tags")).json()
    remaining = next(t for t in tags if t["id"] == tag["id"])
    assert remaining["person_count"] == 0

    await authed_client.delete(f"/api/people/{pid}")
    await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_unassign_unknown_person_or_tag_404(authed_client: AsyncClient) -> None:
    """Unassigning against a missing person or tag id is a 404."""
    person = await _create_person(authed_client, "Unassign 404 Check")
    pid = person["id"]
    assert (await authed_client.delete(f"/api/people/{pid}/tags/999999")).status_code == 404
    assert (await authed_client.delete("/api/people/999999/tags/1")).status_code == 404
    await authed_client.delete(f"/api/people/{pid}")


async def test_deleting_person_removes_assignment_but_keeps_tag(
    authed_client: AsyncClient,
) -> None:
    """Deleting a tagged person leaves the tag alive with its count decremented."""
    person = await _create_person(authed_client, "Deletable Tagged Person")
    pid = person["id"]
    tag = (await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Survivor"})).json()

    assert (await authed_client.delete(f"/api/people/{pid}")).status_code == 204

    tags = (await authed_client.get("/api/tags")).json()
    remaining = next(t for t in tags if t["id"] == tag["id"])
    assert remaining["person_count"] == 0

    await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_deleting_tag_removes_assignment_but_keeps_person(
    authed_client: AsyncClient,
) -> None:
    """Deleting a tag leaves the person alive with the tag gone from their card."""
    person = await _create_person(authed_client, "Person Keeps Living")
    pid = person["id"]
    tag = (
        await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Ephemeral"})
    ).json()

    assert (await authed_client.delete(f"/api/tags/{tag['id']}")).status_code == 204

    detail = (await authed_client.get(f"/api/people/{pid}")).json()
    assert detail["tags"] == []

    await authed_client.delete(f"/api/people/{pid}")


async def test_index_filters_by_tag_with_or_semantics_and_composes_with_q(
    authed_client: AsyncClient,
) -> None:
    """`?tags=1` filters to that tag; `?tags=1&tags=2` is OR; both compose with `q`."""
    tagged_a = await _create_person(authed_client, "Tag Filter Alpha")
    tagged_b = await _create_person(authed_client, "Tag Filter Bravo")
    untagged = await _create_person(authed_client, "Tag Filter Untagged")

    tag1 = (
        await authed_client.post(
            f"/api/people/{tagged_a['id']}/tags", json={"name": "Filter Group One"}
        )
    ).json()
    tag2 = (
        await authed_client.post(
            f"/api/people/{tagged_b['id']}/tags", json={"name": "Filter Group Two"}
        )
    ).json()

    only_one = (await authed_client.get("/api/people", params={"tags": tag1["id"]})).json()
    ids = {p["id"] for p in only_one}
    assert tagged_a["id"] in ids
    assert tagged_b["id"] not in ids
    assert untagged["id"] not in ids

    both = (
        await authed_client.get(
            "/api/people", params={"tags": [tag1["id"], tag2["id"]]}
        )
    ).json()
    ids_both = {p["id"] for p in both}
    assert tagged_a["id"] in ids_both
    assert tagged_b["id"] in ids_both
    assert untagged["id"] not in ids_both

    combo = (
        await authed_client.get(
            "/api/people", params={"tags": tag1["id"], "q": "Tag Filter Alpha"}
        )
    ).json()
    assert {p["id"] for p in combo} == {tagged_a["id"]}

    combo_miss = (
        await authed_client.get(
            "/api/people", params={"tags": tag1["id"], "q": "Tag Filter Bravo"}
        )
    ).json()
    assert combo_miss == []

    for person in (tagged_a, tagged_b, untagged):
        await authed_client.delete(f"/api/people/{person['id']}")
    for tag in (tag1, tag2):
        await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_favorite_toggle_does_not_touch_name(authed_client: AsyncClient) -> None:
    """PATCH with only `is_favorite` toggles it without blanking or requiring the name."""
    person = await _create_person(authed_client, "Favorite Toggle")
    pid = person["id"]
    assert person["is_favorite"] is False

    toggled = await authed_client.patch(f"/api/people/{pid}", json={"is_favorite": True})
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()["is_favorite"] is True
    assert toggled.json()["full_name"] == "Favorite Toggle"

    untoggled = await authed_client.patch(f"/api/people/{pid}", json={"is_favorite": False})
    assert untoggled.json()["is_favorite"] is False
    assert untoggled.json()["full_name"] == "Favorite Toggle"

    # The name can still be edited on its own too.
    renamed = await authed_client.patch(f"/api/people/{pid}", json={"full_name": "Renamed Fav"})
    assert renamed.json()["full_name"] == "Renamed Fav"
    assert renamed.json()["is_favorite"] is False

    await authed_client.delete(f"/api/people/{pid}")


async def test_favorites_filter_and_default_sort_ahead(authed_client: AsyncClient) -> None:
    """`?favorites=true` filters to favorites; by default favorites sort ahead of the rest."""
    plain = await _create_person(authed_client, "AAA Favorites Sort Plain")
    fav = await _create_person(authed_client, "ZZZ Favorites Sort Fav")
    await authed_client.patch(f"/api/people/{fav['id']}", json={"is_favorite": True})

    favorites_only = (
        await authed_client.get("/api/people", params={"favorites": "true"})
    ).json()
    ids = {p["id"] for p in favorites_only}
    assert fav["id"] in ids
    assert plain["id"] not in ids

    everyone = (await authed_client.get("/api/people")).json()
    fav_index = next(i for i, p in enumerate(everyone) if p["id"] == fav["id"])
    plain_index = next(i for i, p in enumerate(everyone) if p["id"] == plain["id"])
    assert fav_index < plain_index  # despite "AAA" < "ZZZ" alphabetically

    await authed_client.delete(f"/api/people/{plain['id']}")
    await authed_client.delete(f"/api/people/{fav['id']}")
