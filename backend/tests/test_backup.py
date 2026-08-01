"""Encrypted backup / restore + system summary tests (Phase 3, closes G-36).

The first block is pure `app/core/crypto.py` unit tests (no DB, no HTTP).
The rest exercises the `/api/backup`, `/api/restore`, and
`/api/system/summary` routes end to end.
"""

import io
from typing import Any

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.core.crypto import MAGIC, decrypt, encrypt
from app.core.errors import InvalidInputError

PASSPHRASE = "a very secure backup passphrase!!"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


# --------------------------------------------------------------------------
# app/core/crypto.py — pure functions, no DB.
# --------------------------------------------------------------------------


def test_encrypt_decrypt_round_trip() -> None:
    """Decrypting what `encrypt` produced returns the exact original plaintext."""
    plaintext = b"\x00\x01binary payload with \xff non-utf8 bytes" * 100
    blob = encrypt(plaintext, PASSPHRASE)
    assert blob[:8] == MAGIC
    assert decrypt(blob, PASSPHRASE) == plaintext


def test_decrypt_wrong_passphrase_is_a_clean_domain_error() -> None:
    """A wrong passphrase surfaces as InvalidInputError, never a raw InvalidTag."""
    blob = encrypt(b"top secret payload", PASSPHRASE)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, "a completely different passphrase!!")
    assert "passphrase" in str(excinfo.value).lower()


def test_decrypt_flipped_ciphertext_byte_is_rejected() -> None:
    """A single flipped bit anywhere in the ciphertext/tag fails GCM authentication."""
    blob = bytearray(encrypt(b"some plaintext bytes right here", PASSPHRASE))
    blob[-1] ^= 0xFF
    with pytest.raises(InvalidInputError):
        decrypt(bytes(blob), PASSPHRASE)


def test_decrypt_tampered_header_is_rejected_because_header_is_aad() -> None:
    """Lowering `time_cost` in the header fails, because the header is bound as AAD."""
    blob = bytearray(encrypt(b"payload protected by the header", PASSPHRASE))
    # time_cost lives at header offset 9, 4 bytes big-endian.
    blob[9:13] = (1).to_bytes(4, "big")
    with pytest.raises(InvalidInputError):
        decrypt(bytes(blob), PASSPHRASE)


def test_decrypt_rejects_a_non_dossier_file_on_the_magic() -> None:
    """A file that isn't a Dossier archive (e.g. plain JSON) is rejected on the magic."""
    garbage = b'{"not": "a backup file"}' * 10
    with pytest.raises(InvalidInputError):
        decrypt(garbage, PASSPHRASE)


def test_decrypt_rejects_a_blob_shorter_than_the_header() -> None:
    """A truncated file (shorter than the 46-byte header) is rejected, not a crash."""
    with pytest.raises(InvalidInputError):
        decrypt(b"too short", PASSPHRASE)


def test_decrypt_rejects_an_unsupported_version() -> None:
    """A well-formed header with a future version number is refused."""
    blob = bytearray(encrypt(b"data", PASSPHRASE))
    blob[8] = 2
    with pytest.raises(InvalidInputError):
        decrypt(bytes(blob), PASSPHRASE)


def _mutate_time_cost(blob: bytes, value: int) -> bytes:
    """Overwrite a blob's header `time_cost` field (offset 9, 4 bytes big-endian)."""
    mutated = bytearray(blob)
    mutated[9:13] = value.to_bytes(4, "big")
    return bytes(mutated)


def _mutate_memory_cost(blob: bytes, value: int) -> bytes:
    """Overwrite a blob's header `memory_cost` field (offset 13, 4 bytes big-endian)."""
    mutated = bytearray(blob)
    mutated[13:17] = value.to_bytes(4, "big")
    return bytes(mutated)


def _mutate_parallelism(blob: bytes, value: int) -> bytes:
    """Overwrite a blob's header `parallelism` field (offset 17, 1 byte)."""
    mutated = bytearray(blob)
    mutated[17:18] = value.to_bytes(1, "big")
    return bytes(mutated)


# Each test below starts from a blob encrypted with cheap *default* params
# (fast to set up) and then overwrites a single header field to an
# out-of-range value. The header is AAD, so the forged blob's GCM tag no
# longer matches — but that must never be why `decrypt` raises here: it must
# reject on the parameter bounds *before* it ever reaches key derivation or
# tag verification. Asserting the specific "unsupported encryption
# parameters" message (rather than just "raises") is what proves the bounds
# check fired instead of the tag-mismatch fallback. `memory_cost` above the
# ceiling additionally uses a magnitude (512 MiB) large enough that, if the
# bounds check ever regressed, a real derivation at that size would be
# conspicuously slow — a canary on top of the message assertion.


def test_decrypt_rejects_memory_cost_above_the_ceiling_before_deriving() -> None:
    """A header asking for far more memory than the 256 MiB ceiling is rejected outright."""
    blob = _mutate_memory_cost(encrypt(b"payload", PASSPHRASE), 524288)  # 512 MiB
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_decrypt_rejects_memory_cost_below_the_floor() -> None:
    """A header asking for near-zero memory is rejected, not silently accepted."""
    blob = _mutate_memory_cost(encrypt(b"payload", PASSPHRASE), 1)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_decrypt_rejects_time_cost_of_zero() -> None:
    """A header asking for zero iterations is rejected."""
    blob = _mutate_time_cost(encrypt(b"payload", PASSPHRASE), 0)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_decrypt_rejects_time_cost_far_above_the_ceiling() -> None:
    """A header asking for an absurd iteration count is rejected, not attempted."""
    blob = _mutate_time_cost(encrypt(b"payload", PASSPHRASE), 50)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_decrypt_rejects_parallelism_of_zero() -> None:
    """A header asking for zero parallelism is rejected."""
    blob = _mutate_parallelism(encrypt(b"payload", PASSPHRASE), 0)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_decrypt_rejects_parallelism_far_above_the_ceiling() -> None:
    """A header asking for absurd parallelism is rejected, not attempted."""
    blob = _mutate_parallelism(encrypt(b"payload", PASSPHRASE), 64)
    with pytest.raises(InvalidInputError) as excinfo:
        decrypt(blob, PASSPHRASE)
    assert "unsupported encryption parameters" in str(excinfo.value).lower()


def test_encrypt_decrypt_round_trip_with_in_range_non_default_parameters() -> None:
    """Legitimate non-default-but-in-range parameters still decrypt (forward compatibility)."""
    plaintext = b"payload encrypted with tuned-but-sane KDF parameters"
    blob = encrypt(plaintext, PASSPHRASE, time_cost=2, memory_cost=8192, parallelism=2)
    assert decrypt(blob, PASSPHRASE) == plaintext


def test_encrypt_refuses_parameters_its_own_decrypt_would_reject() -> None:
    """`encrypt` can't mint an archive that `decrypt` then refuses to open (G-40).

    The bounds check exists to defend `decrypt` against a hostile header, but
    applying it on the way in too is what stops us writing a backup nobody —
    including this build — can ever read again.
    """
    with pytest.raises(InvalidInputError):
        encrypt(b"payload", PASSPHRASE, memory_cost=999_999)
    with pytest.raises(InvalidInputError):
        encrypt(b"payload", PASSPHRASE, time_cost=0)
    with pytest.raises(InvalidInputError):
        encrypt(b"payload", PASSPHRASE, parallelism=99)


# --------------------------------------------------------------------------
# HTTP layer.
# --------------------------------------------------------------------------


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


async def _cleanup(client: AsyncClient, *names: str) -> None:
    """Delete every person whose name matches, so tests stay order-free."""
    for name in names:
        found = (await client.get("/api/people", params={"q": name})).json()
        for person in found:
            await client.delete(f"/api/people/{person['id']}")


def _minimal_person(person_id: int, name: str, **overrides: Any) -> dict:
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


def _minimal_envelope(**overrides: Any) -> dict:
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


async def test_system_summary_counts_uploads_and_last_backup(authed_client: AsyncClient) -> None:
    """Counts/bytes reflect what's stored; `last_backup_at` flips null -> set (G-36).

    This must be the first test in the module to call `/api/backup` — it is
    the only place that asserts `last_backup_at is None`, which is only true
    before the very first backup of the whole test session.
    """
    before = (await authed_client.get("/api/system/summary")).json()
    assert before["last_backup_at"] is None

    first = await _create_person(authed_client, "Summary Person One")
    second = await _create_person(authed_client, "Summary Person Two")
    await _add_field(authed_client, first["id"], "Summary Field", "value")
    await authed_client.post(f"/api/people/{first['id']}/tags", json={"name": "Summary Tag"})
    uploaded = await authed_client.post(
        f"/api/people/{first['id']}/documents",
        files={"file": ("scan.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    linked = await authed_client.post(
        "/api/relationships",
        json={"person_id": first["id"], "related_person_id": second["id"], "type": "sibling"},
    )
    assert linked.status_code == 201, linked.text

    after = (await authed_client.get("/api/system/summary")).json()
    assert after["people"] == before["people"] + 2
    assert after["fields"] == before["fields"] + 4 + 4 + 1  # 4 system fields/person + 1 custom
    assert after["documents"] == before["documents"] + 1
    assert after["relationships"] == before["relationships"] + 1
    assert after["tags"] == before["tags"] + 1
    assert after["uploads_bytes"] == before["uploads_bytes"] + len(PNG_BYTES)
    assert after["database_bytes"] > 0

    backup = await authed_client.post("/api/backup", json={"passphrase": PASSPHRASE})
    assert backup.status_code == 200, backup.text

    final = (await authed_client.get("/api/system/summary")).json()
    assert final["last_backup_at"] is not None

    tags = (await authed_client.get("/api/tags")).json()
    tag_id = next(t["id"] for t in tags if t["name"] == "Summary Tag")
    await _cleanup(authed_client, "Summary Person One", "Summary Person Two")
    await authed_client.delete(f"/api/tags/{tag_id}")


async def test_system_summary_requires_authentication(client: AsyncClient) -> None:
    """The summary route sits behind the auth guard (SEC-1)."""
    assert (await client.get("/api/system/summary")).status_code == 401


async def test_backup_and_restore_require_authentication(client: AsyncClient) -> None:
    """Both routes sit behind the auth guard (SEC-1), independent of CSRF."""
    await client.get("/api/auth/status")  # seeds the CSRF cookie
    headers = {"x-csrf-token": client.cookies["dossier_csrf"]}

    backup = await client.post("/api/backup", json={"passphrase": PASSPHRASE}, headers=headers)
    assert backup.status_code == 401

    restore = await client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(b"irrelevant"), "application/octet-stream")},
        data={"passphrase": PASSPHRASE},
        headers=headers,
    )
    assert restore.status_code == 401


async def test_backup_rejects_a_too_short_passphrase(authed_client: AsyncClient) -> None:
    """A passphrase under 12 characters is refused with a 400, not attempted."""
    response = await authed_client.post("/api/backup", json={"passphrase": "short"})
    assert response.status_code == 400


async def test_restore_rejects_a_too_short_passphrase(authed_client: AsyncClient) -> None:
    """The same length rule applies to the multipart form field on restore."""
    response = await authed_client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(b"irrelevant"), "application/octet-stream")},
        data={"passphrase": "short"},
    )
    assert response.status_code == 400


async def test_restore_rejects_a_non_backup_file_cleanly(authed_client: AsyncClient) -> None:
    """A plain JSON export (or any non-Dossier-backup file) is rejected on the magic."""
    response = await authed_client.post(
        "/api/restore",
        files={
            "file": (
                "not-a-backup.json",
                io.BytesIO(b'{"schema_version": 1, "generator": "dossier"}'),
                "application/json",
            )
        },
        data={"passphrase": PASSPHRASE},
    )
    assert response.status_code == 400
    assert "backup" in response.json()["detail"].lower()


async def test_restore_wrong_passphrase_is_a_clean_400(authed_client: AsyncClient) -> None:
    """A wrong passphrase against a real backup file is a clean domain error, not a 500."""
    backup = await authed_client.post("/api/backup", json={"passphrase": PASSPHRASE})
    assert backup.status_code == 200, backup.text

    response = await authed_client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(backup.content), "application/octet-stream")},
        data={"passphrase": "a totally different passphrase!!"},
    )
    assert response.status_code == 400
    assert "passphrase" in response.json()["detail"].lower()


async def test_backup_refuses_when_the_archive_exceeds_the_configured_limit(
    authed_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plaintext archive is checked against `DOSSIER_MAX_BACKUP_MB` before encrypting."""
    tiny = get_settings().model_copy(update={"max_backup_mb": 0})
    monkeypatch.setattr("app.services.backup_service.get_settings", lambda: tiny)

    response = await authed_client.post("/api/backup", json={"passphrase": PASSPHRASE})
    assert response.status_code == 413


async def test_restore_refuses_a_file_larger_than_the_configured_limit(
    authed_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The multipart upload is capped while streaming in, not after buffering it whole."""
    tiny = get_settings().model_copy(update={"max_backup_mb": 0})
    monkeypatch.setattr("app.routers.backup.get_settings", lambda: tiny)

    response = await authed_client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(b"x" * 100), "application/octet-stream")},
        data={"passphrase": PASSPHRASE},
    )
    assert response.status_code == 413


async def test_backup_restore_full_flow_round_trip(authed_client: AsyncClient) -> None:
    """Create -> backup -> wipe everyone -> restore brings back data *and* files (G-36)."""
    parent = await _create_person(authed_client, "Backup Parent")
    child = await _create_person(authed_client, "Backup Child")
    await _add_field(authed_client, parent["id"], "Vault code", "s3cr3t", type_="sensitive")
    favorited = await authed_client.patch(
        f"/api/people/{parent['id']}", json={"is_favorite": True}
    )
    assert favorited.status_code == 200, favorited.text
    tag = (
        await authed_client.post(f"/api/people/{parent['id']}/tags", json={"name": "Backup Tag"})
    ).json()

    uploaded = await authed_client.post(
        f"/api/people/{parent['id']}/documents",
        files={"file": ("scan.png", io.BytesIO(PNG_BYTES), "image/png")},
        data={"title": "Backup Document"},
    )
    assert uploaded.status_code == 201, uploaded.text

    photo = await authed_client.put(
        f"/api/people/{parent['id']}/photo",
        files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert photo.status_code == 200, photo.text

    link = await authed_client.post(
        "/api/relationships",
        json={
            "person_id": child["id"],
            "related_person_id": parent["id"],
            "type": "parent",
            "related_role": "mother",
        },
    )
    assert link.status_code == 201, link.text

    backup = await authed_client.post("/api/backup", json={"passphrase": PASSPHRASE})
    assert backup.status_code == 200, backup.text
    assert backup.headers["content-type"] == "application/octet-stream"
    assert "attachment" in backup.headers["content-disposition"]
    assert ".dossier" in backup.headers["content-disposition"]
    assert backup.headers["x-content-type-options"] == "nosniff"
    assert backup.headers["cache-control"] == "private, no-store"
    archive = backup.content

    assert (await authed_client.delete(f"/api/people/{parent['id']}")).status_code == 204
    assert (await authed_client.delete(f"/api/people/{child['id']}")).status_code == 204
    assert (await authed_client.get("/api/people", params={"q": "Backup Parent"})).json() == []

    restore = await authed_client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(archive), "application/octet-stream")},
        data={"passphrase": PASSPHRASE},
    )
    assert restore.status_code == 200, restore.text
    report = restore.json()
    assert report["people_created"] == 2
    assert report["documents_restored"] == 1
    assert report["documents_skipped"] == 0
    assert report["relationships_created"] == 1
    assert report["sensitive_values_missing"] == 0  # backups always include sensitive values

    restored_parents = (
        await authed_client.get("/api/people", params={"q": "Backup Parent"})
    ).json()
    assert len(restored_parents) == 1
    parent_id = restored_parents[0]["id"]
    parent_detail = (await authed_client.get(f"/api/people/{parent_id}")).json()
    assert parent_detail["is_favorite"] is True
    assert [t["name"] for t in parent_detail["tags"]] == ["Backup Tag"]
    assert parent_detail["has_photo"] is True
    vault_field = next(f for f in parent_detail["fields"] if f["label"] == "Vault code")
    assert vault_field["value"] == "s3cr3t"
    assert len(parent_detail["documents"]) == 1
    document = parent_detail["documents"][0]
    assert document["title"] == "Backup Document"

    download = await authed_client.get(f"/api/documents/{document['id']}/download")
    assert download.status_code == 200
    assert download.content == PNG_BYTES

    photo_download = await authed_client.get(f"/api/people/{parent_id}/photo")
    assert photo_download.status_code == 200
    assert photo_download.content == PNG_BYTES

    restored_children = (
        await authed_client.get("/api/people", params={"q": "Backup Child"})
    ).json()
    child_detail = (await authed_client.get(f"/api/people/{restored_children[0]['id']}")).json()
    assert len(child_detail["relationships"]) == 1
    assert child_detail["relationships"][0]["label"] == "Mother"

    # Restoring the same backup again is additive: no duplicate people/docs/links.
    again = await authed_client.post(
        "/api/restore",
        files={"file": ("backup.dossier", io.BytesIO(archive), "application/octet-stream")},
        data={"passphrase": PASSPHRASE},
    )
    assert again.status_code == 200, again.text
    again_report = again.json()
    assert again_report["people_created"] == 0
    assert again_report["people_skipped"] == 2

    still_one_parent = (
        await authed_client.get("/api/people", params={"q": "Backup Parent"})
    ).json()
    assert len(still_one_parent) == 1

    await _cleanup(authed_client, "Backup Parent", "Backup Child")
    await authed_client.delete(f"/api/tags/{tag['id']}")


async def test_v1_schema_export_payload_still_imports(authed_client: AsyncClient) -> None:
    """A schema-v1 file predates tags/is_favorite/storage_path/photo_path — all default."""
    payload = _minimal_envelope(
        schema_version=1, people=[_minimal_person(1, "Backup Compat V1")]
    )
    response = await authed_client.post("/api/import", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["people_created"] == 1

    await _cleanup(authed_client, "Backup Compat V1")


async def test_v2_schema_export_payload_still_imports(authed_client: AsyncClient) -> None:
    """A schema-v2 file has tags/is_favorite but predates storage_path/photo_path."""
    payload = _minimal_envelope(
        schema_version=2,
        people=[
            _minimal_person(1, "Backup Compat V2", is_favorite=True, tags=["Compat Tag"])
        ],
    )
    response = await authed_client.post("/api/import", json=payload)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["people_created"] == 1

    restored = (
        await authed_client.get("/api/people", params={"q": "Backup Compat V2"})
    ).json()
    assert restored[0]["is_favorite"] is True
    assert [t["name"] for t in restored[0]["tags"]] == ["Compat Tag"]

    await _cleanup(authed_client, "Backup Compat V2")
    tags = (await authed_client.get("/api/tags")).json()
    compat_tag = next(t for t in tags if t["name"] == "Compat Tag")
    await authed_client.delete(f"/api/tags/{compat_tag['id']}")
