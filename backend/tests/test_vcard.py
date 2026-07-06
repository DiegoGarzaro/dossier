"""vCard export tests (Phase 3, new idea)."""

from httpx import AsyncClient


async def _create_person(client: AsyncClient, name: str) -> dict:
    response = await client.post("/api/people", json={"full_name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def _add_field(
    client: AsyncClient, person_id: int, label: str, value: str, type_: str = "text"
) -> None:
    response = await client.post(
        f"/api/people/{person_id}/fields",
        json={"label": label, "value": value, "type": type_},
    )
    assert response.status_code == 201, response.text


async def test_vcard_basic_shape(authed_client: AsyncClient) -> None:
    """A bare person still produces a valid, minimal vCard."""
    person = await _create_person(authed_client, "Jane Doe")
    response = await authed_client.get(f"/api/people/{person['id']}/vcard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vcard")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"

    body = response.text
    assert body.startswith("BEGIN:VCARD\r\n")
    assert "VERSION:4.0\r\n" in body
    assert "FN:Jane Doe\r\n" in body
    assert "N:Doe;Jane;;;\r\n" in body
    assert body.rstrip().endswith("END:VCARD")
    await authed_client.delete(f"/api/people/{person['id']}")


async def test_vcard_maps_address_email_phone(authed_client: AsyncClient) -> None:
    """Address/Email/Phone-ish field labels map to their standard vCard properties."""
    person = await _create_person(authed_client, "Alex Rivera")
    pid = person["id"]
    await _add_field(authed_client, pid, "Address", "123 Main St")
    await _add_field(authed_client, pid, "Email", "alex@example.com")
    await _add_field(authed_client, pid, "Mobile", "+1-555-0100")

    body = (await authed_client.get(f"/api/people/{pid}/vcard")).text
    assert "ADR:;;123 Main St;;;;\r\n" in body
    assert "EMAIL:alex@example.com\r\n" in body
    assert "TEL:+1-555-0100\r\n" in body
    await authed_client.delete(f"/api/people/{pid}")


async def test_vcard_excludes_sensitive_values(authed_client: AsyncClient) -> None:
    """Sensitive field values (and their labels) never appear in the export (SEC-7)."""
    person = await _create_person(authed_client, "Sam Secret")
    pid = person["id"]
    await _add_field(authed_client, pid, "SSN", "123-45-6789", type_="sensitive")

    body = (await authed_client.get(f"/api/people/{pid}/vcard")).text
    assert "123-45-6789" not in body
    assert "SSN" not in body
    await authed_client.delete(f"/api/people/{pid}")


async def test_vcard_other_fields_land_in_note(authed_client: AsyncClient) -> None:
    """Fields with no standard mapping fall back to NOTE lines, booleans as Yes/No."""
    person = await _create_person(authed_client, "Nia Custom")
    pid = person["id"]
    await _add_field(authed_client, pid, "Favorite color", "teal")
    await _add_field(authed_client, pid, "Newsletter", "true", type_="boolean")

    body = (await authed_client.get(f"/api/people/{pid}/vcard")).text
    assert "Favorite color: teal" in body
    assert "Newsletter: Yes" in body
    await authed_client.delete(f"/api/people/{pid}")


async def test_vcard_escapes_special_characters(authed_client: AsyncClient) -> None:
    """Commas/semicolons in values are escaped so the vCard stays well-formed."""
    person = await _create_person(authed_client, "O'Brien, Sean")
    body = (await authed_client.get(f"/api/people/{person['id']}/vcard")).text
    assert "FN:O'Brien\\, Sean\r\n" in body
    await authed_client.delete(f"/api/people/{person['id']}")


async def test_vcard_includes_related(authed_client: AsyncClient) -> None:
    """Relationships appear as RELATED lines with a standard TYPE param when known (FR-23)."""
    alice = await _create_person(authed_client, "Alice VCard")
    bob = await _create_person(authed_client, "Bob VCard")
    await authed_client.post(
        "/api/relationships",
        json={"person_id": bob["id"], "related_person_id": alice["id"], "type": "parent"},
    )
    body = (await authed_client.get(f"/api/people/{bob['id']}/vcard")).text
    assert "RELATED;TYPE=parent:Alice VCard\r\n" in body
    for person in (alice, bob):
        await authed_client.delete(f"/api/people/{person['id']}")


async def test_vcard_not_found(authed_client: AsyncClient) -> None:
    """A nonexistent person 404s."""
    response = await authed_client.get("/api/people/999999/vcard")
    assert response.status_code == 404
