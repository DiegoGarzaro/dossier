"""JSON import / restore-from-export tests (Phase 3, FR-30 / G3)."""

from typing import Any

from httpx import AsyncClient


def _person(person_id: int, name: str, **overrides: Any) -> dict:
    """Build a minimal exported person, mirroring the export envelope."""
    person = {
        "id": person_id,
        "full_name": name,
        "has_photo": False,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "fields": [],
        "documents": [],
    }
    person.update(overrides)
    return person


def _envelope(**overrides: Any) -> dict:
    """Build a minimal export envelope for import."""
    envelope = {
        "schema_version": 1,
        "generator": "dossier",
        "exported_at": "2026-01-01T00:00:00",
        "scope": "dataset",
        "includes_sensitive_values": False,
        "people": [],
        "relationships": [],
    }
    envelope.update(overrides)
    return envelope


async def _cleanup(client: AsyncClient, *names: str) -> None:
    """Delete every person whose name matches, so tests stay order-free."""
    for name in names:
        found = (await client.get("/api/people", params={"q": name})).json()
        for person in found:
            await client.delete(f"/api/people/{person['id']}")


async def test_import_requires_authentication(client: AsyncClient) -> None:
    """The import route sits behind the auth guard (SEC-1)."""
    await client.get("/api/auth/status")  # seeds the CSRF cookie
    response = await client.post(
        "/api/import",
        json=_envelope(),
        headers={"x-csrf-token": client.cookies["dossier_csrf"]},
    )
    assert response.status_code == 401


async def test_import_round_trip_restores_person_and_fields(authed_client: AsyncClient) -> None:
    """Export → delete → import brings the record back field-for-field (FR-30)."""
    created = await authed_client.post("/api/people", json={"full_name": "Round Trip"})
    person_id = created.json()["id"]
    await authed_client.patch(
        f"/api/fields/{created.json()['fields'][1]['id']}", json={"value": "1990-05-04"}
    )
    await authed_client.post(
        f"/api/people/{person_id}/fields",
        json={"label": "Blood type", "value": "AB-", "type": "text", "is_pinned": True},
    )
    await authed_client.post(
        f"/api/people/{person_id}/fields",
        json={"label": "Card PIN", "value": "1234", "type": "sensitive"},
    )

    exported = (
        await authed_client.get(
            f"/api/people/{person_id}/export", params={"include_sensitive": "true"}
        )
    ).json()
    before = (await authed_client.get(f"/api/people/{person_id}")).json()["fields"]
    assert (await authed_client.delete(f"/api/people/{person_id}")).status_code == 204

    response = await authed_client.post("/api/import", json=exported)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["people_created"] == 1
    assert report["people_skipped"] == 0
    assert report["fields_created"] == len(before)

    restored = (await authed_client.get("/api/people", params={"q": "Round Trip"})).json()
    assert len(restored) == 1
    detail = (await authed_client.get(f"/api/people/{restored[0]['id']}")).json()
    assert [(f["label"], f["value"], f["type"], f["is_pinned"], f["is_system"]) for f in
            detail["fields"]] == [
        (f["label"], f["value"], f["type"], f["is_pinned"], f["is_system"]) for f in before
    ]

    await _cleanup(authed_client, "Round Trip")


async def test_import_skips_a_person_whose_name_already_exists(
    authed_client: AsyncClient,
) -> None:
    """Importing twice is safe: the second run adds nothing (non-destructive)."""
    payload = _envelope(people=[_person(1, "Import Duplicate")])

    first = (await authed_client.post("/api/import", json=payload)).json()
    assert first["people_created"] == 1

    second = (await authed_client.post("/api/import", json=payload)).json()
    assert second["people_created"] == 0
    assert second["people_skipped"] == 1
    assert any("already exists" in warning for warning in second["warnings"])

    found = (await authed_client.get("/api/people", params={"q": "Import Duplicate"})).json()
    assert len(found) == 1  # no duplicate created

    await _cleanup(authed_client, "Import Duplicate")


async def test_import_never_overwrites_an_existing_person(authed_client: AsyncClient) -> None:
    """A skipped person keeps their stored values — import is additive only."""
    created = await authed_client.post("/api/people", json={"full_name": "Import Untouched"})
    person_id = created.json()["id"]
    document_field = created.json()["fields"][0]
    await authed_client.patch(f"/api/fields/{document_field['id']}", json={"value": "KEEP-ME"})

    payload = _envelope(
        people=[
            _person(
                99,
                "Import Untouched",
                fields=[
                    {
                        "label": "Document number",
                        "value": "OVERWRITE-ME",
                        "type": "text",
                        "is_pinned": True,
                        "is_system": True,
                        "position": 0,
                        "value_omitted": False,
                    }
                ],
            )
        ]
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["people_skipped"] == 1
    assert report["fields_created"] == 0

    detail = (await authed_client.get(f"/api/people/{person_id}")).json()
    stored = next(f for f in detail["fields"] if f["label"] == "Document number")
    assert stored["value"] == "KEEP-ME"

    await _cleanup(authed_client, "Import Untouched")


async def test_import_restores_relationships_with_roles(authed_client: AsyncClient) -> None:
    """Links are recreated between imported people, keeping the gendered role (G-31)."""
    payload = _envelope(
        people=[_person(1, "Import Mother"), _person(2, "Import Kid")],
        relationships=[
            {
                "person_a_id": 1,
                "person_a_name": "Import Mother",
                "person_b_id": 2,
                "person_b_name": "Import Kid",
                "type": "parent",
                "custom_label": None,
                "role_a": "mother",
                "role_b": None,
            }
        ],
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["people_created"] == 2
    assert report["relationships_created"] == 1
    assert report["relationships_skipped"] == 0

    kid = (await authed_client.get("/api/people", params={"q": "Import Kid"})).json()[0]
    detail = (await authed_client.get(f"/api/people/{kid['id']}")).json()
    assert len(detail["relationships"]) == 1
    assert detail["relationships"][0]["label"] == "Mother"
    assert detail["relationships"][0]["person_name"] == "Import Mother"

    await _cleanup(authed_client, "Import Mother", "Import Kid")


async def test_import_skips_a_relationship_it_cannot_resolve(authed_client: AsyncClient) -> None:
    """A link pointing at somebody not in the file (and not on file) is reported, not fatal."""
    payload = _envelope(
        people=[_person(1, "Import Lonely")],
        relationships=[
            {
                "person_a_id": 1,
                "person_a_name": "Import Lonely",
                "person_b_id": 77,
                "person_b_name": "Missing Person",
                "type": "sibling",
                "custom_label": None,
                "role_a": None,
                "role_b": None,
            }
        ],
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["people_created"] == 1
    assert report["relationships_created"] == 0
    assert report["relationships_skipped"] == 1
    assert any("Missing Person" in warning for warning in report["warnings"])

    await _cleanup(authed_client, "Import Lonely")


async def test_import_leaves_withheld_sensitive_values_empty(authed_client: AsyncClient) -> None:
    """A `value_omitted` field imports blank and is reported, never as a null overwrite (SEC-7)."""
    payload = _envelope(
        people=[
            _person(
                1,
                "Import Secretless",
                fields=[
                    {
                        "label": "Vault code",
                        "value": None,
                        "type": "sensitive",
                        "is_pinned": False,
                        "is_system": False,
                        "position": 0,
                        "value_omitted": True,
                    }
                ],
            )
        ]
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["sensitive_values_missing"] == 1

    person = (await authed_client.get("/api/people", params={"q": "Import Secretless"})).json()[0]
    detail = (await authed_client.get(f"/api/people/{person['id']}")).json()
    field = next(f for f in detail["fields"] if f["label"] == "Vault code")
    assert field["value"] is None
    assert field["type"] == "sensitive"

    await _cleanup(authed_client, "Import Secretless")


async def test_import_reports_documents_it_cannot_restore(authed_client: AsyncClient) -> None:
    """Document metadata can't rebuild a file, so it's skipped and surfaced (G-36)."""
    payload = _envelope(
        people=[
            _person(
                1,
                "Import Docs",
                documents=[
                    {
                        "title": "Birth certificate",
                        "original_filename": "scan.png",
                        "mime_type": "image/png",
                        "size_bytes": 40,
                        "uploaded_at": "2026-01-01T00:00:00",
                    }
                ],
            )
        ]
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["documents_skipped"] == 1
    assert any("document" in warning.lower() for warning in report["warnings"])

    person = (await authed_client.get("/api/people", params={"q": "Import Docs"})).json()[0]
    detail = (await authed_client.get(f"/api/people/{person['id']}")).json()
    assert detail["documents"] == []

    await _cleanup(authed_client, "Import Docs")


async def test_import_rejects_a_newer_schema_version(authed_client: AsyncClient) -> None:
    """A file from a future Dossier is refused with a clear message, not half-applied."""
    response = await authed_client.post(
        "/api/import", json=_envelope(schema_version=99, people=[_person(1, "Import Future")])
    )
    assert response.status_code == 400
    assert "newer" in response.json()["detail"].lower()
    assert (await authed_client.get("/api/people", params={"q": "Import Future"})).json() == []


async def test_import_rejects_a_foreign_file(authed_client: AsyncClient) -> None:
    """Some other app's JSON is refused rather than partially interpreted."""
    response = await authed_client.post(
        "/api/import",
        json=_envelope(generator="not-dossier", people=[_person(1, "Import Foreign")]),
    )
    assert response.status_code == 400
    assert (await authed_client.get("/api/people", params={"q": "Import Foreign"})).json() == []


async def test_import_round_trip_preserves_tags_and_favorite_flag(
    authed_client: AsyncClient,
) -> None:
    """Export -> delete -> import brings back the favorite flag and tags ("Organizing people")."""
    created = await authed_client.post(
        "/api/people", json={"full_name": "Import Tags Round Trip"}
    )
    person_id = created.json()["id"]
    await authed_client.patch(f"/api/people/{person_id}", json={"is_favorite": True})
    tag = (
        await authed_client.post(
            f"/api/people/{person_id}/tags", json={"name": "Round Trip Tag"}
        )
    ).json()

    exported = (await authed_client.get(f"/api/people/{person_id}/export")).json()
    assert exported["people"][0]["is_favorite"] is True
    assert exported["people"][0]["tags"] == ["Round Trip Tag"]

    assert (await authed_client.delete(f"/api/people/{person_id}")).status_code == 204
    assert (await authed_client.delete(f"/api/tags/{tag['id']}")).status_code == 204

    report = (await authed_client.post("/api/import", json=exported)).json()
    assert report["people_created"] == 1

    restored = (
        await authed_client.get("/api/people", params={"q": "Import Tags Round Trip"})
    ).json()
    assert len(restored) == 1
    assert restored[0]["is_favorite"] is True
    assert [t["name"] for t in restored[0]["tags"]] == ["Round Trip Tag"]
    restored_tag_id = restored[0]["tags"][0]["id"]

    await _cleanup(authed_client, "Import Tags Round Trip")
    await authed_client.delete(f"/api/tags/{restored_tag_id}")


async def test_import_skipped_person_keeps_their_existing_tags_untouched(
    authed_client: AsyncClient,
) -> None:
    """Import is additive: a skipped (already-existing) person's tags are never changed."""
    created = await authed_client.post(
        "/api/people", json={"full_name": "Import Skip Keeps Tags"}
    )
    person_id = created.json()["id"]
    kept_tag = (
        await authed_client.post(
            f"/api/people/{person_id}/tags", json={"name": "Kept Tag"}
        )
    ).json()

    payload = _envelope(
        people=[
            _person(
                99,
                "Import Skip Keeps Tags",
                is_favorite=True,
                tags=["Should Not Attach"],
            )
        ]
    )
    report = (await authed_client.post("/api/import", json=payload)).json()
    assert report["people_skipped"] == 1

    detail = (await authed_client.get(f"/api/people/{person_id}")).json()
    assert detail["is_favorite"] is False  # skipped person's flag stays untouched too
    assert [t["name"] for t in detail["tags"]] == ["Kept Tag"]

    stray = (await authed_client.get("/api/tags")).json()
    assert all(t["name"] != "Should Not Attach" for t in stray)

    await authed_client.delete(f"/api/people/{person_id}")
    await authed_client.delete(f"/api/tags/{kept_tag['id']}")


async def test_import_v1_schema_payload_without_tags_key_still_imports(
    authed_client: AsyncClient,
) -> None:
    """A schema-v1 file (no `tags`/`is_favorite` keys) still imports cleanly (backward compat)."""
    # `_person()`'s base dict has no `tags`/`is_favorite` keys, exactly like a real v1 file —
    # the schema's field defaults (False / []) must fill the gap.
    v1_person = _person(1, "Import Legacy V1 Payload")
    assert "tags" not in v1_person
    assert "is_favorite" not in v1_person
    payload = _envelope(schema_version=1, people=[v1_person])

    response = await authed_client.post("/api/import", json=payload)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["people_created"] == 1

    restored = (
        await authed_client.get("/api/people", params={"q": "Import Legacy V1 Payload"})
    ).json()
    assert len(restored) == 1
    assert restored[0]["is_favorite"] is False
    assert restored[0]["tags"] == []

    await _cleanup(authed_client, "Import Legacy V1 Payload")


async def test_import_validates_field_values_against_their_type(
    authed_client: AsyncClient,
) -> None:
    """A tampered file can't smuggle a bad value past FR-14 validation."""
    payload = _envelope(
        people=[
            _person(
                1,
                "Import Invalid",
                fields=[
                    {
                        "label": "Date of birth",
                        "value": "not-a-date",
                        "type": "date",
                        "is_pinned": True,
                        "is_system": True,
                        "position": 0,
                        "value_omitted": False,
                    }
                ],
            )
        ]
    )
    response = await authed_client.post("/api/import", json=payload)
    assert response.status_code == 400
    assert (await authed_client.get("/api/people", params={"q": "Import Invalid"})).json() == []
