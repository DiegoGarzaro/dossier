"""People + fields + documents flow tests (Epics B, C, D)."""

import io

from httpx import AsyncClient

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # valid PNG magic, dummy body
)


async def _create_person(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def test_person_crud_and_default_pinned_fields(authed_client: AsyncClient) -> None:
    """Create → read → rename → delete; creation seeds pinned fields (FR-6/17/8/9)."""
    person = await _create_person(authed_client, "Test Person CRUD")
    labels = [field["label"] for field in person["fields"]]
    assert labels == ["Document number", "Address", "Nationality"]
    assert all(field["is_pinned"] for field in person["fields"])

    renamed = await authed_client.patch(
        f"/api/people/{person['id']}", json={"full_name": "Renamed Person"}
    )
    assert renamed.json()["full_name"] == "Renamed Person"

    assert (await authed_client.delete(f"/api/people/{person['id']}")).status_code == 204
    assert (await authed_client.get(f"/api/people/{person['id']}")).status_code == 404


async def test_name_search(authed_client: AsyncClient) -> None:
    """Index search matches names case-insensitively (FR-26)."""
    person = await _create_person(authed_client, "Zulmira Searchable")
    found = (await authed_client.get("/api/people", params={"q": "zulmira"})).json()
    assert any(entry["id"] == person["id"] for entry in found)
    await authed_client.delete(f"/api/people/{person['id']}")


async def test_field_lifecycle_and_type_validation(authed_client: AsyncClient) -> None:
    """Add/edit/pin/reorder/remove fields; values validated by type (Epic C, FR-14)."""
    person = await _create_person(authed_client, "Fields Person")
    pid = person["id"]

    bad = await authed_client.post(
        f"/api/people/{pid}/fields",
        json={"label": "Birth date", "value": "not-a-date", "type": "date"},
    )
    assert bad.status_code == 400

    created = await authed_client.post(
        f"/api/people/{pid}/fields",
        json={"label": "Blood type", "value": "O+", "type": "text"},
    )
    assert created.status_code == 201
    field = created.json()
    assert field["position"] == 3  # after the three seeded pinned fields

    pinned = await authed_client.patch(f"/api/fields/{field['id']}", json={"is_pinned": True})
    assert pinned.json()["is_pinned"] is True

    detail = (await authed_client.get(f"/api/people/{pid}")).json()
    reversed_ids = [entry["id"] for entry in reversed(detail["fields"])]
    reorder = await authed_client.post(
        f"/api/people/{pid}/fields/reorder",
        json={"items": [{"id": fid, "position": pos} for pos, fid in enumerate(reversed_ids)]},
    )
    assert reorder.status_code == 200
    assert [entry["id"] for entry in reorder.json()] == reversed_ids
    assert reorder.json()[0]["id"] == field["id"]  # our field was last, now first

    assert (await authed_client.delete(f"/api/fields/{field['id']}")).status_code == 204
    await authed_client.delete(f"/api/people/{pid}")


async def test_system_fields_are_protected(authed_client: AsyncClient) -> None:
    """Seeded fields are system fields: value/pin editable, label/type/delete locked (FR-17)."""
    person = await _create_person(authed_client, "System Fields Person")
    pid = person["id"]
    assert all(field["is_system"] for field in person["fields"])
    system_field = person["fields"][0]

    # Value and pin stay editable.
    value_edit = await authed_client.patch(
        f"/api/fields/{system_field['id']}", json={"value": "AB-123456"}
    )
    assert value_edit.status_code == 200
    assert value_edit.json()["value"] == "AB-123456"

    # Label, type, unpinning, and delete are locked.
    label_edit = await authed_client.patch(
        f"/api/fields/{system_field['id']}", json={"label": "Renamed"}
    )
    assert label_edit.status_code == 400
    type_edit = await authed_client.patch(
        f"/api/fields/{system_field['id']}", json={"type": "number"}
    )
    assert type_edit.status_code == 400
    unpin = await authed_client.patch(
        f"/api/fields/{system_field['id']}", json={"is_pinned": False}
    )
    assert unpin.status_code == 400
    assert (await authed_client.delete(f"/api/fields/{system_field['id']}")).status_code == 400

    # Custom fields are unaffected.
    custom = (
        await authed_client.post(f"/api/people/{pid}/fields", json={"label": "Nickname"})
    ).json()
    assert custom["is_system"] is False
    assert (await authed_client.delete(f"/api/fields/{custom['id']}")).status_code == 204
    await authed_client.delete(f"/api/people/{pid}")


async def test_document_upload_download_delete(authed_client: AsyncClient) -> None:
    """Upload validates content, download is an attachment, delete removes both (Epic D)."""
    person = await _create_person(authed_client, "Documents Person")
    pid = person["id"]

    fake = await authed_client.post(
        f"/api/people/{pid}/documents",
        files={"file": ("evil.png", io.BytesIO(b"MZ not a png"), "image/png")},
    )
    assert fake.status_code == 400  # magic bytes don't match the extension (SEC-6)

    uploaded = await authed_client.post(
        f"/api/people/{pid}/documents",
        files={"file": ("scan.png", io.BytesIO(PNG_BYTES), "image/png")},
        data={"title": "Birth certificate"},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["title"] == "Birth certificate"
    assert document["mime_type"] == "image/png"

    download = await authed_client.get(f"/api/documents/{document['id']}/download")
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment")
    assert download.headers["x-content-type-options"] == "nosniff"

    assert (await authed_client.delete(f"/api/documents/{document['id']}")).status_code == 204
    await authed_client.delete(f"/api/people/{pid}")
