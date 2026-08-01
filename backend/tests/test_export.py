"""JSON export tests (Phase 3, FR-30 / G3)."""

import io

from httpx import AsyncClient

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def _create_person(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def _add_field(
    client: AsyncClient, person_id: int, label: str, value: str, type_: str = "text"
) -> dict:
    response = await client.post(
        f"/api/people/{person_id}/fields",
        json={"label": label, "value": value, "type": type_},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_export_requires_authentication(client: AsyncClient) -> None:
    """Both export endpoints sit behind the auth guard (SEC-1)."""
    assert (await client.get("/api/export")).status_code == 401
    assert (await client.get("/api/people/1/export")).status_code == 401


async def test_person_export_envelope_and_fields(authed_client: AsyncClient) -> None:
    """A person export is a versioned envelope carrying the person's fields (FR-30)."""
    person = await _create_person(authed_client, "Export Envelope")
    await _add_field(authed_client, person["id"], "Blood type", "O+")

    response = await authed_client.get(f"/api/people/{person['id']}/export")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert "Export-Envelope.json" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"

    payload = response.json()
    assert payload["schema_version"] == 2
    assert payload["generator"] == "dossier"
    assert payload["scope"] == "person"
    assert payload["includes_sensitive_values"] is False
    assert payload["exported_at"]

    assert len(payload["people"]) == 1
    exported = payload["people"][0]
    assert exported["id"] == person["id"]
    assert exported["full_name"] == "Export Envelope"
    assert exported["has_photo"] is False
    labels = {field["label"]: field for field in exported["fields"]}
    assert labels["Blood type"]["value"] == "O+"
    assert labels["Blood type"]["type"] == "text"
    # Seeded system fields keep their flags so an import can restore them (FR-17).
    assert labels["Document number"]["is_system"] is True
    assert labels["Document number"]["is_pinned"] is True

    await authed_client.delete(f"/api/people/{person['id']}")


async def test_person_export_omits_sensitive_values_by_default(
    authed_client: AsyncClient,
) -> None:
    """Sensitive values never leave in a default export; the field itself still does (SEC-7)."""
    person = await _create_person(authed_client, "Export Sensitive")
    await _add_field(authed_client, person["id"], "Passport PIN", "9182", type_="sensitive")

    response = await authed_client.get(f"/api/people/{person['id']}/export")
    assert response.status_code == 200
    assert "9182" not in response.text  # not anywhere in the raw payload

    payload = response.json()
    assert payload["includes_sensitive_values"] is False
    field = next(f for f in payload["people"][0]["fields"] if f["label"] == "Passport PIN")
    assert field["type"] == "sensitive"
    assert field["value"] is None
    assert field["value_omitted"] is True

    await authed_client.delete(f"/api/people/{person['id']}")


async def test_person_export_includes_sensitive_when_opted_in(
    authed_client: AsyncClient,
) -> None:
    """`include_sensitive=true` is an explicit opt-in for a full-fidelity backup (SEC-7)."""
    person = await _create_person(authed_client, "Export Sensitive Optin")
    await _add_field(authed_client, person["id"], "Passport PIN", "9182", type_="sensitive")

    response = await authed_client.get(
        f"/api/people/{person['id']}/export", params={"include_sensitive": "true"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["includes_sensitive_values"] is True
    field = next(f for f in payload["people"][0]["fields"] if f["label"] == "Passport PIN")
    assert field["value"] == "9182"
    assert field["value_omitted"] is False

    await authed_client.delete(f"/api/people/{person['id']}")


async def test_person_export_document_metadata_excludes_storage_path(
    authed_client: AsyncClient,
) -> None:
    """Documents export as metadata only — never the on-disk random filename (SEC-6)."""
    person = await _create_person(authed_client, "Export Documents")
    uploaded = await authed_client.post(
        f"/api/people/{person['id']}/documents",
        files={"file": ("scan.png", io.BytesIO(PNG_BYTES), "image/png")},
        data={"title": "Birth certificate"},
    )
    assert uploaded.status_code == 201, uploaded.text

    response = await authed_client.get(f"/api/people/{person['id']}/export")
    payload = response.json()
    documents = payload["people"][0]["documents"]
    assert len(documents) == 1
    document = documents[0]
    assert document["title"] == "Birth certificate"
    assert document["original_filename"] == "scan.png"
    assert document["mime_type"] == "image/png"
    assert document["size_bytes"] == len(PNG_BYTES)
    assert "storage_path" not in document
    assert "_photos" not in response.text

    await authed_client.delete(f"/api/people/{person['id']}")


async def test_person_export_includes_only_own_relationships(
    authed_client: AsyncClient,
) -> None:
    """A person-scoped export carries the links that touch that person, with names."""
    mother = await _create_person(authed_client, "Export Mother")
    child = await _create_person(authed_client, "Export Child")
    stranger = await _create_person(authed_client, "Export Stranger")
    created = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": child["id"],
            "related_person_id": mother["id"],
            "type": "parent",
            "related_role": "mother",
        },
    )
    assert created.status_code == 201, created.text

    response = await authed_client.get(f"/api/people/{child['id']}/export")
    payload = response.json()
    assert len(payload["relationships"]) == 1
    link = payload["relationships"][0]
    # Stored canonically: the parent is always person_a (Architecture §4.2).
    assert link["person_a_id"] == mother["id"]
    assert link["person_a_name"] == "Export Mother"
    assert link["person_b_id"] == child["id"]
    assert link["person_b_name"] == "Export Child"
    assert link["type"] == "parent"
    assert link["role_a"] == "mother"

    stranger_export = (await authed_client.get(f"/api/people/{stranger['id']}/export")).json()
    assert stranger_export["relationships"] == []

    for person in (mother, child, stranger):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_dataset_export_covers_every_person_and_link(authed_client: AsyncClient) -> None:
    """The dataset export is the whole vault in one file (FR-30 / G3)."""
    first = await _create_person(authed_client, "Export Dataset One")
    second = await _create_person(authed_client, "Export Dataset Two")
    created = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": first["id"],
            "related_person_id": second["id"],
            "type": "sibling",
        },
    )
    assert created.status_code == 201, created.text

    response = await authed_client.get("/api/export")
    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    assert "dossier-export-" in response.headers["content-disposition"]

    payload = response.json()
    assert payload["scope"] == "dataset"
    exported_ids = {person["id"] for person in payload["people"]}
    assert {first["id"], second["id"]} <= exported_ids
    pairs = {(link["person_a_id"], link["person_b_id"]) for link in payload["relationships"]}
    assert (first["id"], second["id"]) in pairs

    for person in (first, second):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_dataset_export_omits_sensitive_values_by_default(
    authed_client: AsyncClient,
) -> None:
    """The safe default holds for the whole-dataset export too (SEC-7)."""
    person = await _create_person(authed_client, "Export Dataset Sensitive")
    await _add_field(authed_client, person["id"], "Vault code", "hunter2", type_="sensitive")

    response = await authed_client.get("/api/export")
    assert "hunter2" not in response.text

    opted_in = await authed_client.get("/api/export", params={"include_sensitive": "true"})
    assert "hunter2" in opted_in.text

    await authed_client.delete(f"/api/people/{person['id']}")


async def test_person_export_unknown_person_returns_404(authed_client: AsyncClient) -> None:
    """Exporting a missing person is a clean 404, not a 500."""
    assert (await authed_client.get("/api/people/999999/export")).status_code == 404


async def test_export_carries_favorite_flag_and_tag_names(authed_client: AsyncClient) -> None:
    """The favorite flag and tag names travel in both export scopes ("Organizing people")."""
    person = await _create_person(authed_client, "Export Tags And Favorite")
    pid = person["id"]
    await authed_client.patch(f"/api/people/{pid}", json={"is_favorite": True})
    tag = (
        await authed_client.post(f"/api/people/{pid}/tags", json={"name": "Export Tag"})
    ).json()

    person_export = (await authed_client.get(f"/api/people/{pid}/export")).json()
    assert person_export["schema_version"] == 2
    exported = person_export["people"][0]
    assert exported["is_favorite"] is True
    assert exported["tags"] == ["Export Tag"]

    dataset_export = (await authed_client.get("/api/export")).json()
    exported_in_dataset = next(p for p in dataset_export["people"] if p["id"] == pid)
    assert exported_in_dataset["is_favorite"] is True
    assert exported_in_dataset["tags"] == ["Export Tag"]

    await authed_client.delete(f"/api/people/{pid}")
    await authed_client.delete(f"/api/tags/{tag['id']}")
