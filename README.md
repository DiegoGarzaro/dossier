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

Everything persistent lives in `./data` (SQLite database + uploads):

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
