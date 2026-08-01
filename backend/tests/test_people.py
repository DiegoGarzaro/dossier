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
    assert labels == ["Document number", "Date of birth", "Address", "Nationality"]
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


async def _add_field(client: AsyncClient, pid: int, label: str, value: str, type_: str) -> dict:
    response = await client.post(
        f"/api/people/{pid}/fields", json={"label": label, "value": value, "type": type_}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_field_value_search_off_by_default(authed_client: AsyncClient) -> None:
    """Without fields=true, a query matching only a field value doesn't match (FR-27)."""
    person = await _create_person(authed_client, "Fieldsearch Default")
    pid = person["id"]
    await _add_field(authed_client, pid, "Blood type", "AB-negative", "text")

    # Name doesn't contain the query; field search is opt-in, so no hit.
    found = (await authed_client.get("/api/people", params={"q": "AB-negative"})).json()
    assert all(entry["id"] != pid for entry in found)

    await authed_client.delete(f"/api/people/{pid}")


async def test_field_value_search_matches_and_surfaces_field(authed_client: AsyncClient) -> None:
    """fields=true matches non-sensitive field values and reports the hit (FR-27)."""
    person = await _create_person(authed_client, "Fieldsearch Hit")
    pid = person["id"]
    await _add_field(authed_client, pid, "Blood type", "AB-negative", "text")

    found = (
        await authed_client.get("/api/people", params={"q": "ab-negative", "fields": "true"})
    ).json()
    entry = next((e for e in found if e["id"] == pid), None)
    assert entry is not None  # matched case-insensitively via the field value
    assert [f["label"] for f in entry["matched_fields"]] == ["Blood type"]

    await authed_client.delete(f"/api/people/{pid}")


async def test_field_value_search_excludes_sensitive(authed_client: AsyncClient) -> None:
    """Sensitive field values are never searchable and never surfaced (SEC-7 / G-16)."""
    person = await _create_person(authed_client, "Fieldsearch Secret")
    pid = person["id"]
    await _add_field(authed_client, pid, "SSN", "SECRET-999-XYZ", "sensitive")

    found = (
        await authed_client.get("/api/people", params={"q": "SECRET-999-XYZ", "fields": "true"})
    ).json()
    # The sensitive value must not make the person findable...
    assert all(entry["id"] != pid for entry in found)
    # ...and even if the person appeared for another reason, the value stays out.
    all_people = (await authed_client.get("/api/people", params={"fields": "true"})).json()
    entry = next((e for e in all_people if e["id"] == pid), None)
    assert entry is not None
    assert all("SECRET" not in (f["value"] or "") for f in entry["matched_fields"])

    await authed_client.delete(f"/api/people/{pid}")


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
    assert field["position"] == 4  # after the four seeded pinned fields

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


async def test_stored_type_still_validates_on_update(authed_client: AsyncClient) -> None:
    """Editing only the value of an existing typed field still validates it (G-37).

    Regression guard: the `type` column is a plain String, so a field read back
    from the database holds a `str`. `validate_value` used `is` comparisons,
    which never matched, and every update that didn't also resend `type` skipped
    validation entirely.
    """
    person = await _create_person(authed_client, "Stored Type Person")
    pid = person["id"]
    created = await authed_client.post(
        f"/api/people/{pid}/fields",
        json={"label": "Shoe size", "value": "42", "type": "number"},
    )
    assert created.status_code == 201
    field_id = created.json()["id"]

    # Value-only PATCH: the type comes from the stored row, not the request.
    bad = await authed_client.patch(f"/api/fields/{field_id}", json={"value": "not-a-number"})
    assert bad.status_code == 400
    assert (await authed_client.get(f"/api/people/{pid}")).json()["fields"][-1]["value"] == "42"

    await authed_client.delete(f"/api/people/{pid}")


async def test_sensitive_pinned_values_hidden_from_index(authed_client: AsyncClient) -> None:
    """Pinned sensitive values never appear in the index-grid preview (SEC-7)."""
    person = await _create_person(authed_client, "Secret Pinner")
    created = await authed_client.post(
        f"/api/people/{person['id']}/fields",
        json={"label": "PIN code", "value": "9-8-7-6", "type": "sensitive", "is_pinned": True},
    )
    assert created.status_code == 201

    listing = (await authed_client.get("/api/people", params={"q": "Secret Pinner"})).json()
    entry = next(item for item in listing if item["id"] == person["id"])
    assert all(field["type"] != "sensitive" for field in entry["pinned_fields"])
    assert "9-8-7-6" not in str(entry)
    await authed_client.delete(f"/api/people/{person['id']}")


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


async def test_date_of_birth_is_a_protected_date_field(authed_client: AsyncClient) -> None:
    """Date of birth is seeded as a pinned, system, `date`-typed field (FR-17)."""
    person = await _create_person(authed_client, "Birthday Person")
    pid = person["id"]
    birth = next(field for field in person["fields"] if field["label"] == "Date of birth")
    assert birth["type"] == "date"
    assert birth["is_system"] is True
    assert birth["is_pinned"] is True
    assert birth["value"] is None

    # Being a `date` field, the value is validated on write (FR-14).
    bad = await authed_client.patch(f"/api/fields/{birth['id']}", json={"value": "not-a-date"})
    assert bad.status_code == 400
    good = await authed_client.patch(f"/api/fields/{birth['id']}", json={"value": "1985-04-12"})
    assert good.status_code == 200, good.text
    assert good.json()["value"] == "1985-04-12"

    # System-field protections apply (G-24/G-25): no rename, retype, unpin, or delete.
    assert (
        await authed_client.patch(f"/api/fields/{birth['id']}", json={"label": "Birthday"})
    ).status_code == 400
    assert (
        await authed_client.patch(f"/api/fields/{birth['id']}", json={"type": "text"})
    ).status_code == 400
    assert (
        await authed_client.patch(f"/api/fields/{birth['id']}", json={"is_pinned": False})
    ).status_code == 400
    assert (await authed_client.delete(f"/api/fields/{birth['id']}")).status_code == 400

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
