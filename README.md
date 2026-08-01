# Dossier

> Your people, on file.

A self-hosted, authenticated people-records vault where each person is an ID-card-style
record: a few pinned fields shown prominently, unlimited custom fields, uploaded
documents, and (Phase 2) links between people.

Documentation lives in [`docs/`](docs/):
- [Product & Software Requirements](docs/Product%20&%20Software%20Requirements.md)
- [Design System](docs/Design%20System.md) — palette, typography, components
- [Architecture](docs/Architecture.md) — stack, data model, API, security

## Stack

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy 2.0, SQLite (WAL), Alembic, Argon2id — managed with [uv](https://docs.astral.sh/uv/)
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS v4 — served as static files by the backend
- **Deploy:** single Docker container, one `/data` volume

## Development

Backend (http://localhost:8000):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Frontend dev server with API proxy (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

`npm run build` type-checks and writes the production bundle into
`backend/app/static/`, where the backend serves it.

### Checks

```bash
cd backend
uv run ruff check .
uv run pytest
```

## Production (Docker)

```bash
docker compose up -d
```

Open http://localhost:8080 — the first run walks you through creating the admin
account (no default credentials). Migrations run automatically on start.

## Backup & restore

There are two ways to back up a vault. Use the encrypted backup for the data you actually
care about (people, fields, documents, photos); use the `/data` volume backup for full disaster
recovery of the container itself (it additionally covers the admin account and active sessions,
which the encrypted backup deliberately does not touch).

### Encrypted backup (data + uploaded files)

From Settings, or directly against the API:

```bash
curl -X POST http://localhost:8080/api/backup \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" -b "dossier_session=$SESSION;dossier_csrf=$CSRF" \
  -d '{"passphrase": "a long, memorable passphrase"}' \
  -o dossier-backup.dossier
```

This downloads one `.dossier` file: a single AES-256-GCM-encrypted archive containing the full
JSON data export (**with `sensitive` field values included**, unlike the plain JSON export below —
that's the point of encrypting it) plus every uploaded document and profile photo. The passphrase
must be 12–1024 characters; it is never stored, logged, or sent anywhere but into the key
derivation below.

To restore, `POST` the file back with the same passphrase (`POST /api/restore`, multipart
`file` + `passphrase` fields). Restoring is **additive**, exactly like the plain JSON import: a
person whose name is already on file is left untouched and skipped rather than overwritten, so
restoring the same backup twice never creates duplicates.

#### File format

The `.dossier` file is a 46-byte header followed by an AES-256-GCM ciphertext (16-byte tag
appended). It's deliberately simple enough to decrypt with a short script and no Dossier code:

```
offset size  field
0      8     magic          b"DOSSIER1"
8      1     version        uint8, currently 1
9      4     time_cost      uint32, big-endian (Argon2id parameter)
13     4     memory_cost    uint32, big-endian, in KiB (Argon2id parameter)
17     1     parallelism    uint8 (Argon2id parameter)
18     16    salt           random, unique per backup
34     12    nonce          random, unique per backup (AES-GCM nonce)
46     ...   ciphertext, with its 16-byte GCM tag appended
```

The key is 32 bytes, derived with **Argon2id**:

```python
from argon2.low_level import Type, hash_secret_raw

key = hash_secret_raw(
    secret=passphrase.encode("utf-8"),
    salt=salt,               # bytes 18:34 of the file
    time_cost=time_cost,     # bytes 9:13, big-endian uint32
    memory_cost=memory_cost, # bytes 13:17, big-endian uint32, KiB
    parallelism=parallelism, # byte 17
    hash_len=32,
    type=Type.ID,
)
```

Defaults are `time_cost=3`, `memory_cost=65536` (64 MiB), `parallelism=4` — but always read them
back from the header rather than assuming these, since a future Dossier version could change them.

The **entire 46-byte header is passed as AES-GCM's associated data (AAD)**, not just encrypted
alongside it:

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

header = blob[:46]
nonce = blob[34:46]
plaintext = AESGCM(key).decrypt(nonce, blob[46:], header)  # raises InvalidTag if wrong/tampered
```

Binding the header as AAD means the KDF parameters are cryptographically tied to the ciphertext:
tampering with so much as one header byte (e.g. lowering `time_cost` to make brute-forcing
cheaper) invalidates the GCM tag, even if a new key is derived from the tampered parameters. A
wrong passphrase and a corrupted/tampered file both fail the same way (`InvalidTag`) — there is no
way to distinguish the two from outside.

`plaintext` is a gzipped tar (`tarfile`/`tar xzf` both read it) containing `dossier.json` (the
full data export) and an `uploads/` directory mirroring the app's upload storage layout.

### Plain `/data` volume backup (whole container state)

Everything persistent — SQLite database, uploads, and unlike the encrypted backup above, the
admin account and active sessions — lives in `./data`:

```bash
docker compose stop
tar czf dossier-backup-$(date +%F).tar.gz data/
docker compose start
```

To restore: stop the container, replace `./data` with the backup contents,
start again — migrations reconcile the schema if the app was updated.

## Security notes

- All data routes require an authenticated session (HTTP-only, SameSite cookie).
- CSRF protection via double-submit token on every state-changing request.
- Passwords hashed with Argon2id; sessions are server-side and revocable.
- Uploads are allow-listed (PDF/PNG/JPG/WEBP), magic-byte checked, stored under
  random names, and served as attachment downloads.
- Intended for home-LAN use. If exposing beyond the LAN, put a reverse proxy
  with HTTPS in front and set `DOSSIER_TRUST_PROXY=true`.
