# Dossier — Architecture

> **Status:** Draft v1.0 — companion to *Product & Software Requirements.md* and *Design System.md*.
> **Scope:** Technical architecture for the MVP (Epics A–D + name search + backup), with Phase-2 relationships accounted for in the data model.
> **Confirmed decisions (from requirements §12 defaults):** D1 single shared admin login · D2 LAN/HTTP, reverse-proxy for external HTTPS · D3 React + Vite + Tailwind · D4 SQLite · D6 six field types for MVP.

---

## 1. Architecture overview

Single Docker container. The FastAPI backend serves both the JSON API and the pre-built React static bundle. SQLite file and the uploads directory live on a mounted volume so data survives container recreation (FR-28).

```
                    ┌──────────────────────────────────────────────┐
   Browser  ─────▶  │  Docker container: dossier                   │
   (LAN)            │                                              │
                    │   ┌────────────────────────────────────┐     │
                    │   │ FastAPI (uvicorn, async)           │     │
                    │   │  • /api/*    JSON API              │     │
                    │   │  • /*        React static bundle   │     │
                    │   │  • session cookie auth + CSRF      │     │
                    │   └───────────────┬────────────────────┘     │
                    │                   │ async SQLAlchemy          │
                    │        ┌──────────┴──────────┐                │
                    │        ▼                     ▼                │
                    │  /data/app.db          /data/uploads/         │
                    │  (SQLite, WAL)         (files)                │
                    └──────────────────────────────────────────────┘
                                   │ bind mount / named volume
                                   ▼
                             Host: ./data  (backed up)
```

**Optional external access (D2):** a reverse proxy (Caddy/Traefik/nginx) terminates HTTPS and forwards to the container. The app honors `X-Forwarded-*` headers.

---

## 2. Technology stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | managed with **uv** |
| Web framework | **FastAPI** | async endpoints throughout |
| ASGI server | uvicorn (via gunicorn worker in prod) | single worker fine at this scale |
| ORM | **SQLAlchemy 2.0 async** + `aiosqlite` | async sessions per request |
| Migrations | **Alembic** | run automatically on startup (NFR-8) |
| DB | **SQLite** (WAL mode) | one file; Postgres = future upgrade path |
| Validation | Pydantic v2 | request/response schemas |
| Auth | server-side sessions | signed HTTP-only SameSite cookie; Argon2id via `argon2-cffi` |
| Files | local filesystem | `/data/uploads`, metadata in DB |
| Frontend | **React 18 + Vite + TypeScript + Tailwind** | built to static, served by backend |
| Data fetching | TanStack Query + fetch wrapper | cache + optimistic field edits |
| Routing | React Router | |
| Testing | pytest + pytest-asyncio + httpx (BE), Vitest + Testing Library (FE) | |
| Lint/format | **ruff** (BE), ESLint + Prettier (FE) | `ruff check .` before every handover |
| Container | Docker multi-stage | stage 1 build FE, stage 2 Python runtime |

Backend conventions (per project rules): async SQLAlchemy queries and async methods throughout; layered structure honoring SOLID; Google-style docstrings with typed `Args`/`Returns`.

---

## 3. Backend structure

Layered, dependency-inverted: **routers → services → repositories → models**. Routers do HTTP only; services hold business rules; repositories own all DB access (so persistence is swappable and testable).

```
backend/
  app/
    main.py                 # app factory, static mount, startup (migrations)
    config.py               # Pydantic Settings (env-driven)
    db.py                   # async engine, session factory, get_session dep
    security.py             # hashing, session, CSRF helpers
    deps.py                 # FastAPI dependencies (current_user, csrf, session)
    models/                 # SQLAlchemy ORM models
      base.py               # DeclarativeBase, TimestampMixin
      user.py people.py field.py document.py relationship.py
    schemas/                # Pydantic request/response models
    repositories/           # async data access, one per aggregate
      people_repo.py field_repo.py document_repo.py relationship_repo.py user_repo.py
    services/               # business logic, validation, orchestration
      auth_service.py people_service.py field_service.py
      document_service.py relationship_service.py backup_service.py
    routers/                # FastAPI routers under /api
      auth.py people.py fields.py documents.py relationships.py search.py system.py
    core/                   # errors, pagination, file validation
    static/                 # built React bundle (copied in Docker build)
  alembic/                  # migrations
  tests/
  pyproject.toml            # uv-managed
```

**Request lifecycle:** middleware (session load, CSRF check on unsafe methods) → router → `Depends(get_current_user)` → service → repository → async DB session (one per request, committed by the router/service boundary).

---

## 4. Data model

Refined from requirements §6. All tables carry `created_at` / `updated_at` (UTC) via a `TimestampMixin`. SQLite with `PRAGMA foreign_keys=ON` and WAL.

### 4.1 Entities

**users**
| col | type | notes |
|---|---|---|
| id | INTEGER PK | |
| username | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | Argon2id |
| created_at, updated_at | DATETIME | |

**people**
| col | type | notes |
|---|---|---|
| id | INTEGER PK | |
| full_name | TEXT NOT NULL | indexed (search FR-26) |
| photo_path | TEXT NULL | relative path under uploads |
| created_at, updated_at | DATETIME | |

**fields** — EAV flexible store (delivers "infinite add/remove fields")
| col | type | notes |
|---|---|---|
| id | INTEGER PK | |
| person_id | INTEGER FK→people ON DELETE CASCADE | indexed |
| label | TEXT NOT NULL | |
| value | TEXT NULL | stored as text; typed on validation/read |
| type | TEXT NOT NULL | enum: text\|textarea\|number\|date\|boolean\|sensitive |
| is_pinned | BOOLEAN NOT NULL default 0 | |
| position | INTEGER NOT NULL | ordering within a person |
| created_at, updated_at | DATETIME | |
| | | index `(person_id, position)` |

**documents**
| col | type | notes |
|---|---|---|
| id | INTEGER PK | |
| person_id | INTEGER FK→people ON DELETE CASCADE | indexed |
| title | TEXT NOT NULL | |
| original_filename | TEXT NOT NULL | sanitized for display |
| mime_type | TEXT NOT NULL | validated allow-list |
| size_bytes | INTEGER NOT NULL | |
| storage_path | TEXT NOT NULL | opaque server path (uuid filename) |
| uploaded_at | DATETIME | |

**relationships** (Phase 2, modeled now)
| col | type | notes |
|---|---|---|
| id | INTEGER PK | |
| person_a_id | INTEGER FK→people ON DELETE CASCADE | |
| person_b_id | INTEGER FK→people ON DELETE CASCADE | |
| type | TEXT NOT NULL | spouse\|parent\|child\|sibling\|custom |
| custom_label | TEXT NULL | inverse-aware label when custom |
| created_at | DATETIME | |
| | | CHECK `person_a_id <> person_b_id`; UNIQUE `(person_a_id, person_b_id, type)` |

**sessions** (server-side session store — table so sessions survive restart and can be revoked)
| col | type | notes |
|---|---|---|
| id | TEXT PK | random 256-bit token id (the cookie value) |
| user_id | INTEGER FK→users ON DELETE CASCADE | |
| created_at | DATETIME | |
| expires_at | DATETIME | idle window, default 14 days (FR-4) |

### 4.2 Relationship directionality (Phase 2)

Stored once as an ordered pair. On read, the service composes each person's view and derives the **inverse label** (FR-23): `parent`→shows as `child` on the other side and vice-versa; `spouse`/`sibling` are symmetric; `custom` mirrors `custom_label` unless an inverse is supplied. To create a `child` link the service normalizes to a `parent` row (so the pair/type is canonical and the unique constraint holds).

---

## 5. API contract

REST under `/api`. JSON. All state-changing requests require the CSRF token header. All routes except `/api/auth/*` and static assets require a valid session (FR-1).

### Auth
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/auth/status` | `{ initialized, authenticated }` — drives first-run vs login |
| POST | `/api/auth/setup` | first-run: create initial admin (only if no users exist) (FR-5) |
| POST | `/api/auth/login` | set session cookie |
| POST | `/api/auth/logout` | invalidate session (FR-4) |
| POST | `/api/auth/password` | change password (FR-3) |

### People
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/people?q=` | list/grid; `q` name search (FR-10, FR-26) |
| POST | `/api/people` | create (full_name required) (FR-6) |
| GET | `/api/people/{id}` | full ID-card payload (person + fields + documents + relationships) |
| PATCH | `/api/people/{id}` | edit name (FR-8) |
| PUT | `/api/people/{id}/photo` | upload/replace profile image |
| DELETE | `/api/people/{id}` | delete + cascade (FR-9) |

### Fields
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/people/{id}/fields` | add field (FR-11/12) |
| PATCH | `/api/fields/{id}` | edit label/value/type/pinned (FR-15/16) |
| DELETE | `/api/fields/{id}` | remove (FR-15) |
| POST | `/api/people/{id}/fields/reorder` | `[{id, position}]` bulk reorder (FR-15) |

### Documents
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/people/{id}/documents` | multipart upload (FR-18/20) |
| GET | `/api/documents/{id}/download` | stream as attachment (SEC-6) |
| PATCH | `/api/documents/{id}` | rename title (FR-D2) |
| DELETE | `/api/documents/{id}` | delete file + metadata (FR-21) |

### Relationships (Phase 2) · Search · System
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/relationships` | create link (FR-22/24) |
| DELETE | `/api/relationships/{id}` | remove (FR-25) |
| GET | `/api/search?q=&fields=true` | name + optional field-value search (FR-27, Phase 3) |
| GET | `/api/system/health` | liveness |
| GET | `/api/system/export` | JSON export (nice-to-have, FR-30) |

**Conventions:** cursor/offset pagination on list endpoints; RFC-7807-style error bodies; `sensitive` field values returned normally over the authenticated API but masked client-side by default (reveal is a UI action) — and excluded from field-value search indexing where feasible (FR-27 / SEC-7).

An OpenAPI schema is auto-generated by FastAPI at `/api/docs` (dev only); it is the living API spec and supersedes this table.

---

## 6. Authentication & session design

- **First run:** `/api/auth/status` reports `initialized=false` when the `users` table is empty; the UI shows account creation; `/api/auth/setup` creates the single admin and refuses if a user already exists (FR-5, no default credentials).
- **Passwords:** Argon2id (`argon2-cffi`), per-password salt, tuned params; stored as hash only (FR-2 / SEC-2).
- **Sessions:** on login, create a `sessions` row with a 256-bit random id; set it in an **HTTP-only, SameSite=Lax, Secure-when-forwarded-proto=https** cookie. Server-side store means logout and expiry are authoritative and revocable (FR-4).
- **Idle expiry:** `expires_at` = now + configurable window (default 14 days); sliding renewal on activity. Expired/absent → 401.
- **CSRF (SEC-3):** double-submit token. A non-HTTP-only `csrf` cookie + `X-CSRF-Token` header required on POST/PATCH/PUT/DELETE; middleware rejects mismatches. SameSite=Lax is the second layer.

---

## 7. File storage & upload safety

- Files saved under `/data/uploads/{person_id}/{uuid}{ext}`; DB stores `storage_path`, original filename kept only as display metadata (FR-19).
- **Validation (SEC-6, FR-18/20):** allow-list MIME + extension (PDF, PNG, JPG, WEBP); sniff magic bytes, don't trust the client content-type; enforce max size (default 25 MB, configurable) — stream to disk, reject over limit; generate a random filename (never reuse the user's).
- **Serving:** downloads only — `Content-Disposition: attachment`, correct `Content-Type`, `X-Content-Type-Options: nosniff`; files live outside any executable/static-served path and are streamed via an authenticated endpoint, never linked directly.
- Profile images validated as images; stored under `/data/uploads/_photos/`.

---

## 8. Frontend architecture

```
frontend/src/
  main.tsx  App.tsx  router.tsx
  lib/         api client (fetch + CSRF header), query client
  theme/       tokens.css, ThemeProvider (light/dark, localStorage)
  components/  ui/ (Button, Input, Toggle, Dialog, Toast, Badge, Avatar)
               person/ (IdCard, FieldRow, PinnedChip, DocumentRow, RelationshipChip)
  features/    auth/ people/ fields/ documents/ relationships/ search/
  pages/       Login, FirstRun, PeopleIndex, PersonCard, EditPerson, Settings
```

- **State/data:** TanStack Query for server state; local component state for inline edits with **optimistic updates** on field edit/reorder (snappy ID-card).
- **Theme:** semantic CSS variables per *Design System.md*; `.dark` toggled on `<html>`, initialized from `prefers-color-scheme`, persisted.
- **Routing/guards:** unauthenticated → `/login`; uninitialized → `/setup`.
- **Build:** Vite → static assets copied into `backend/app/static`; SPA fallback so client routes resolve (backend serves `index.html` for non-`/api` paths).

---

## 9. Deployment

**Multi-stage Dockerfile:** (1) Node stage builds the React bundle; (2) Python stage installs deps with uv, copies app + built static, runs uvicorn. Targets `amd64` + `arm64` (NFR-1).

**docker-compose.yml (sketch):**
```yaml
services:
  dossier:
    image: dossier:latest
    ports: ["8080:8080"]
    volumes:
      - ./data:/data          # app.db + uploads (survives recreation, FR-28)
    environment:
      - DOSSIER_SESSION_IDLE_DAYS=14
      - DOSSIER_MAX_UPLOAD_MB=25
      - DOSSIER_DATA_DIR=/data
      - DOSSIER_TRUST_PROXY=false          # true behind reverse proxy
    restart: unless-stopped
```

- **Migrations:** Alembic `upgrade head` runs on startup before serving (NFR-8) — `docker compose up` is the only bootstrap step.
- **Reverse proxy (D2):** when `DOSSIER_TRUST_PROXY=true`, honor `X-Forwarded-Proto/For/Host`, mark cookies `Secure`. Docs show a Caddy example for HTTPS.

---

## 10. Backup & restore (FR-28/29, G1/G2)

Because everything persistent is under `./data`, backup = stop-copy-start of one directory.

- **Backup:** `docker compose stop` (or checkpoint WAL) → copy/tar `./data` (contains `app.db`, `app.db-wal`, `app.db-shm`, `uploads/`) → restart. Document a cron example.
- **Restore:** stop container → replace `./data` from a backup → start; migrations reconcile schema version.
- **Export (nice-to-have):** `/api/system/export` returns portable JSON of people/fields/relationships (documents referenced by metadata) (FR-30 / G3).

---

## 11. Security mapping

| Requirement | Implementation |
|---|---|
| SEC-1 / FR-1 | Session dependency on every `/api` route except `/api/auth/*` |
| SEC-2 / FR-2 | Argon2id hashing, salted, hash-only storage |
| SEC-3 | HTTP-only SameSite cookie + double-submit CSRF token |
| SEC-4 | React auto-escapes; no `dangerouslySetInnerHTML`; server stores raw, encodes on output |
| SEC-5 | SQLAlchemy parameterized queries only — no string SQL |
| SEC-6 | Magic-byte validation, random filenames, attachment disposition, `nosniff`, non-executable path |
| SEC-7 | `sensitive` masked by default in UI; excluded from plaintext field search |
| SEC-8 | Reverse-proxy support (forwarded headers), HTTPS documented for external |
| SEC-9 / NFR-2 | No outbound calls; self-hosted fonts/icons; no telemetry |

---

## 12. Testing strategy

- **Backend:** pytest + pytest-asyncio; httpx `AsyncClient` against the app; SQLite in-memory/temp file per test. Cover services (business rules: field typing/validation FR-14, cascade deletes FR-9, relationship inverse FR-23, duplicate/self-link rejection FR-24) and routers (auth guard, CSRF, upload validation).
- **Frontend:** Vitest + Testing Library for ID-card rendering, inline edit, pinned toggle, reorder, sensitive reveal, mode switch.
- **Acceptance:** a checklist mapped to requirements §13 (fresh `docker compose up` → first-run → create person → all six field types → pin → upload → search → unauthenticated 401 → backup/restore round-trip).
- **CI gate:** `ruff check .`, backend tests, `eslint`, FE tests, Docker build.

---

## 13. Traceability & open items

- Every FR in the requirements maps to a table/endpoint/section above; relationships (Epic E) are modeled now but built in Phase 2 per the roadmap.
- **Open (inherited):** D5 product/image name (affects image + compose naming); D6 whether to add `select`/`file` field types for MVP (would extend the `fields.type` enum and add validation + UI); Postgres upgrade path (D4) kept open via the repository layer.
- **Next steps:** confirm the product name (D5) → scaffold repo (`backend/` + `frontend/`) → implement Epic A (auth + first-run) → Epic B/C (people + fields, the ID-card) → Epic D (documents) → search + backup docs.
