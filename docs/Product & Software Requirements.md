# Dossier — Product & Software Requirements

> **Name:** Dossier — *"Your people, on file."* (chosen; resolves D5. Originally drafted as "Family Vault".)
> **Status:** Draft v1.0 — to be reviewed and approved before implementation begins.
> **One-line description:** A self-hosted, authenticated app where each person is an ID-card-style record with a few prominent fields, an unlimited set of custom add/remove fields, uploaded documents, and links to other people (marriage, children, etc.).
>
> **Scope note:** Dossier is for the people in your life generally — family, but also anyone whose records you want to keep in one private place. The "family" framing below reflects the original brief; read it as "people".

---

## 1. Overview & Vision

We accumulate important personal information about the people in our lives — document numbers, blood types, addresses, nationalities, insurance details — that lives scattered across drawers, notes apps, and memory, and is never there when you need it. Dossier is a single private place, running on your own home server, where every person has one clear record you can read at a glance and extend with any field you want.

The interface centers on an **identity card**: a profile picture, the person's name, and a handful of pinned fields (document number, address, nationality) displayed prominently, followed by a flexible list of any other fields you choose to add. Records can be linked to one another to express real family relationships, and documents (PDFs, images) can be attached to each person.

The product deliberately does **not** try to be a relationship/interaction tracker (the direction Monica took that the user disliked). It is a **records vault**, not a CRM.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- **G1** — Store structured personal information for many people in one private, self-hosted place.
- **G2** — Make each person's key information readable at a glance (the ID-card view).
- **G3** — Support unlimited, user-defined custom fields per person, added and removed on demand.
- **G4** — Attach and retrieve documents (IDs, certificates, scans) per person.
- **G5** — Represent family relationships (spouse/marriage, parent/child, sibling, custom).
- **G6** — Protect access with authentication; keep all data on hardware the user controls.
- **G7** — Be easy to deploy and back up via Docker on a home server / NAS.

### 2.2 Non-Goals (out of scope for this product)
- **NG1** — Interaction logging, journaling, reminders, birthday nudges, "keep in touch" prompts (this is what made Monica feel wrong for this use case).
- **NG2** — Multi-tenant / SaaS hosting for unrelated households.
- **NG3** — Native mobile apps (a responsive web UI that works well on a phone browser is sufficient for the MVP).
- **NG4** — Social/sharing features, public profiles, or any outbound data transmission.
- **NG5** — Automated document parsing / OCR (possible future enhancement, not required).

---

## 3. Personas & Primary Use Cases

### 3.1 Personas
- **Owner/Admin (primary):** The household member who installs the app, manages accounts, and maintains records. Comfortable running Docker.
- **Household member (secondary, optional):** Another trusted adult who logs in to read or update records. May or may not exist depending on the chosen auth model (see §11 / Open Decision D1).

### 3.2 Representative use cases
- **UC1** — "What's my son's blood type and health-insurance number?" → open his card, read pinned/custom fields.
- **UC2** — "Add my new passport number and expiry date to my own record." → add two custom fields, one text, one date.
- **UC3** — "Store a scan of my daughter's birth certificate." → upload a PDF to her record.
- **UC4** — "Record that I'm married to my spouse and we have two children." → create relationship links between records.
- **UC5** — "Find whoever has document number ending 4821." → search across field values.
- **UC6** — "A family member moved out; remove their record." → delete a person and associated data.

---

## 4. User Stories (by epic)

### Epic A — Authentication & Access
- **A1** As a user, I must log in before I can see or edit any data.
- **A2** As an admin, I can set/change my password.
- **A3** As a user, my session persists for a reasonable time and I can log out.

### Epic B — People
- **B1** As a user, I can create a new person with at least a full name.
- **B2** As a user, I can view a person's ID-card record.
- **B3** As a user, I can edit a person's name and profile picture.
- **B4** As a user, I can delete a person (with a confirmation step).
- **B5** As a user, I can see a list/grid of all people and open any of them.

### Epic C — Fields (the core of the product)
- **C1** As a user, I can add a custom field to a person by giving it a label and a value.
- **C2** As a user, I can choose the field's type (text, long text, number, date, boolean, sensitive/masked).
- **C3** As a user, I can edit a field's label or value.
- **C4** As a user, I can remove a field.
- **C5** As a user, I can reorder fields.
- **C6** As a user, I can mark a field as "pinned" so it shows in the card header (e.g. document number, address, nationality).

### Epic D — Documents
- **D1** As a user, I can upload one or more files to a person's record.
- **D2** As a user, I can give an uploaded document a title.
- **D3** As a user, I can download a document.
- **D4** As a user, I can delete a document (with confirmation).
- **D5** As a user, I can see document type, size, and upload date.

### Epic E — Relationships
- **E1** As a user, I can link two people with a relationship type (spouse/married, parent, child, sibling, or a custom label).
- **E2** As a user, viewing a person shows their related people, and each link is navigable.
- **E3** As a user, a relationship appears correctly on both people's records (bidirectional, with correct inverse label — e.g. parent ↔ child).
- **E4** As a user, I can remove a relationship.

### Epic F — Search & Navigation
- **F1** As a user, I can search people by name.
- **F2** As a user, I can search across field values (e.g. a document number).

### Epic G — Data Safety
- **G1** As an admin, I can back up all data (database + uploaded files) with a documented, simple procedure.
- **G2** As an admin, I can restore from a backup.
- **G3** *(Nice-to-have)* As a user, I can export a person or all data to a portable JSON file.

---

## 5. Functional Requirements

Each requirement is testable and traceable to the stories above.

### 5.1 Authentication
- **FR-1** The app SHALL require an authenticated session for every route except the login page and static assets.
- **FR-2** Passwords SHALL be stored only as salted hashes (Argon2id or bcrypt), never in plaintext.
- **FR-3** The app SHALL provide login, logout, and password-change functions.
- **FR-4** Sessions SHALL expire after a configurable idle period (default 14 days) and be invalidated on logout.
- **FR-5** The first run SHALL guide creation of the initial admin account (no default credentials shipped).

### 5.2 People
- **FR-6** The app SHALL let a user create a person with a required `full_name` and optional profile image.
- **FR-7** The app SHALL display a person as an ID-card: profile image, full name, pinned fields in the header, all other fields listed below.
- **FR-8** The app SHALL let a user edit `full_name` and profile image.
- **FR-9** The app SHALL let a user delete a person; deletion SHALL require explicit confirmation and SHALL cascade to that person's fields, documents, and relationship links.
- **FR-10** The app SHALL provide an index (grid or list) of all people with name, thumbnail, and a quick way to open each.

### 5.3 Fields
- **FR-11** The app SHALL let a user add an arbitrary number of fields to any person; there is no fixed field schema and no upper limit imposed by the design.
- **FR-12** Each field SHALL have: a label, a value, a type, a pinned flag, and a sort position.
- **FR-13** Supported field types SHALL be at minimum: `text`, `textarea` (long text), `number`, `date`, `boolean`, and `sensitive` (value masked in the UI by default, revealed on demand).
- **FR-14** The app SHALL validate field values against their type (e.g. a `date` field rejects non-dates).
- **FR-15** The app SHALL let a user edit, remove, and reorder fields.
- **FR-16** The app SHALL let a user toggle a field's pinned flag; pinned fields render in the card header.
- **FR-17** *(Convenience)* On person creation, the app MAY pre-populate common pinned fields (document number, address, nationality) as empty, editable, removable fields — matching the reference mockup. These are ordinary fields, not special columns.

### 5.4 Documents
- **FR-18** The app SHALL let a user upload files to a person; allowed types SHALL include at least PDF and common image formats (PNG, JPG, WEBP).
- **FR-19** Uploaded files SHALL be stored on the server filesystem (a mounted volume); the database SHALL store only metadata (title, original filename, MIME type, size, upload timestamp, storage path).
- **FR-20** The app SHALL enforce a configurable maximum upload size (default 25 MB per file).
- **FR-21** The app SHALL let a user download and delete documents; deletion removes both the file and its metadata.

### 5.5 Relationships
- **FR-22** The app SHALL let a user create a relationship between two existing people with a type: `spouse`, `parent`, `child`, `sibling`, or a free-text custom label.
- **FR-23** Relationships SHALL be bidirectional and display the correct inverse on the related person (parent↔child; spouse↔spouse; sibling↔sibling; custom shows the same label both ways unless an inverse is provided).
- **FR-24** The app SHALL prevent obviously invalid links (a person related to themselves; exact duplicate links).
- **FR-25** The app SHALL let a user remove a relationship from either person's record.

### 5.6 Search
- **FR-26** The app SHALL provide a search that matches against person names.
- **FR-27** Search SHALL optionally match against field labels and values, excluding `sensitive`-type values from plaintext indexing where feasible.

### 5.7 Data safety
- **FR-28** The deployment SHALL keep all persistent data (database + uploaded files) on named volumes or bind mounts so they survive container recreation.
- **FR-29** Documentation SHALL describe a backup and restore procedure covering both the database and the uploads volume.
- **FR-30** *(Nice-to-have)* The app MAY provide a JSON export of a single person or the whole dataset.

---

## 6. Data Model

Relational, normalized. Suggested tables:

**users**
- `id` (PK)
- `username`
- `password_hash`
- `created_at`, `updated_at`

**people**
- `id` (PK)
- `full_name`
- `photo_path` (nullable)
- `created_at`, `updated_at`

**fields** — the flexible attribute store (Entity-Attribute-Value pattern)
- `id` (PK)
- `person_id` (FK → people, cascade delete)
- `label`
- `value` (stored as text; typed on read/validation)
- `type` (`text` | `textarea` | `number` | `date` | `boolean` | `sensitive`)
- `is_pinned` (bool)
- `position` (int, for ordering)
- `created_at`, `updated_at`

**documents**
- `id` (PK)
- `person_id` (FK → people, cascade delete)
- `title`
- `original_filename`
- `mime_type`
- `size_bytes`
- `storage_path`
- `uploaded_at`

**relationships**
- `id` (PK)
- `person_a_id` (FK → people, cascade delete)
- `person_b_id` (FK → people, cascade delete)
- `type` (`spouse` | `parent` | `child` | `sibling` | `custom`)
- `custom_label` (nullable, used when `type = custom`)
- `created_at`
- Constraint: `person_a_id != person_b_id`; unique on the ordered pair + type.

> Design note: keeping *everything except name and photo* in the `fields` table is what delivers the "infinite add/remove fields" requirement without schema changes. Document number, address, and nationality from the mockup are simply pinned `fields`, not dedicated columns.

---

## 7. Non-Functional Requirements

- **NFR-1 — Self-hosting:** Ships as a Docker image (single container preferred) deployable via `docker compose` on a typical home server or NAS, amd64 and arm64.
- **NFR-2 — Privacy:** No telemetry, analytics, ads, or any outbound network calls with user data. All processing is local.
- **NFR-3 — Security:** Authenticated access to all data routes; hashed passwords; protection against common web risks (CSRF on state-changing requests, XSS output-encoding, SQL injection via parameterized queries/ORM); uploaded files served as downloads, never executed.
- **NFR-4 — Data durability:** Persistent storage on volumes; documented backup/restore; no data loss across updates.
- **NFR-5 — Usability:** Responsive layout usable on desktop and phone browsers; the ID-card view is the centerpiece and must be clean and legible.
- **NFR-6 — Performance:** Comfortable for a household scale (order of tens to low hundreds of people, hundreds of documents). Person and card views load in well under a second on modest hardware (e.g. Raspberry Pi 4 class).
- **NFR-7 — Maintainability:** Simple, well-documented stack; minimal moving parts; easy to update the image.
- **NFR-8 — Deployability:** No manual database bootstrapping beyond `docker compose up`; migrations run automatically on start.
- **NFR-9 — Accessibility:** Sensible defaults — sufficient contrast, keyboard-navigable forms, labeled inputs.
- **NFR-10 — Internationalization (optional):** Copy externalized so a second language could be added later; not required for MVP.

---

## 8. Architecture & Recommended Tech Stack

A single-container app is ideal for a home self-hoster (one image, one volume set, trivial backups).

**Recommended stack**
- **Backend:** Python + **FastAPI**, with SQLModel/SQLAlchemy for the ORM.
- **Database:** **SQLite** (one file on a mounted volume — perfect at this scale and trivial to back up). Postgres is an optional upgrade path if ever needed.
- **File storage:** Uploaded documents on a mounted volume (e.g. `/data/uploads`), referenced by `storage_path`.
- **Frontend:** **React (Vite) + Tailwind CSS**, built to static files and served by the backend — this gives the design control needed for a polished ID-card UI and a better palette than the mockup's placeholder green.
- **Auth:** Server-side session cookies (HTTP-only, SameSite); Argon2id password hashing.
- **Packaging:** One Docker image (backend serves the built frontend); `docker-compose.yml` with a data volume.

**Lighter alternative:** FastAPI + server-rendered templates + HTMX, if the user prefers to avoid a JS build step. Trades some UI polish for simplicity.

> This stack matches the direction agreed earlier in planning. The choice is confirmable at Open Decision D3.

---

## 9. UI / Screens

Derived from the reference mockup (ID-card layout).

- **Login screen** — username + password; first-run shows account creation instead.
- **People index** — responsive grid of cards (thumbnail + name + a pinned field or two); "Add person" button; search bar.
- **Person / ID-card screen** — the core view:
  - **Header:** profile picture/placeholder on the left; full name large; pinned fields (e.g. document number, address, nationality) beside/under the name.
  - **Fields section:** the full list of custom fields with labels and values; inline edit; **"Add field" / "Remove field"** controls (as shown by the mockup's "Button to Add/Remove field and value").
  - **Documents section:** list of attached files with title, type, size, date; upload, download, delete.
  - **Relationships section:** linked people grouped by relationship (spouse, children, parents, siblings, custom), each navigable; add/remove links.
- **Edit person** — name, profile image.
- **Settings** — change password; backup/export info; (later) manage additional users.

**Design direction:** keep the clean ID-card metaphor from the mockup but replace the placeholder single-green palette with a refined, higher-contrast scheme and clear typographic hierarchy (name > pinned fields > field list). Card should feel like a tidy official document, not a form dump.

---

## 10. Security & Privacy Requirements

- **SEC-1** All data routes behind authentication (FR-1).
- **SEC-2** Passwords hashed with Argon2id/bcrypt (FR-2).
- **SEC-3** CSRF protection on all state-changing requests; HTTP-only, SameSite session cookies.
- **SEC-4** Output encoding to prevent stored XSS in field labels/values.
- **SEC-5** Parameterized queries / ORM only — no string-built SQL.
- **SEC-6** Uploaded files stored outside any executable path and served with a download disposition and correct content-type; filename sanitized.
- **SEC-7** `sensitive`-type fields masked by default in the UI.
- **SEC-8** Intended for home-LAN use over HTTP; if exposed beyond the LAN, deployment docs SHALL require a reverse proxy providing HTTPS. The app SHALL support running behind a reverse proxy (respects forwarded headers).
- **SEC-9** No outbound network calls carrying user data (NFR-2).

---

## 11. MVP Scope & Phased Roadmap

**MVP (must-have to be useful):** Epics A, B, C, D, plus basic name search (F1) and documented backup (G1/G2).
- Auth (login/logout/password, first-run admin).
- People CRUD with profile image.
- Custom fields: add/edit/remove/reorder, all six types, pinned fields in header.
- Documents: upload/download/delete with metadata.
- Backup/restore documentation.

**Phase 2:** Relationships (Epic E) — spouse/parent/child/sibling/custom, bidirectional display.

**Phase 3:** Field-value search (F2), JSON export/import (G3), settings polish.

**Phase 4 (optional):** Multiple user accounts with roles, internationalization, OCR/auto-fill from uploaded IDs, audit log.

---

## 12. Open Decisions & Assumptions

These should be settled before implementation starts; sensible defaults are proposed.

- **D1 — Auth model.** Single shared login, or per-person accounts with permissions? *Default: single shared admin login for the MVP; multi-user deferred to Phase 4.*
- **D2 — Network exposure.** Home-LAN only, or reachable externally? *Default: LAN-only over HTTP; external access requires a reverse proxy with HTTPS (documented, not built-in).*
- **D3 — Frontend approach.** React (Vite + Tailwind) SPA vs. server-rendered + HTMX. *Default: React + Tailwind for UI polish; confirm before scaffolding.*
- **D4 — Database.** SQLite vs. Postgres. *Default: SQLite for simplicity at household scale.*
- **D5 — Product name.** ✅ Resolved: **Dossier**. Package/image use `dossier`; env vars use the `DOSSIER_` prefix.
- **D6 — Field type set.** Confirm the six proposed types (text, textarea, number, date, boolean, sensitive) are enough for the MVP, or whether `select`/dropdown and `file`-typed fields are wanted now vs. later.

**Assumptions:** household scale (tens of people); a single trusted operator; Docker available on the target server; data fits comfortably on local disk; the polished visual design will be defined during implementation, taking the mockup as structural (not palette) guidance.

---

## 13. Acceptance Criteria (MVP "done")

The MVP is complete when:
1. A fresh `docker compose up` yields a running app on a chosen port with a first-run admin setup.
2. A logged-in user can create a person, add/edit/remove/reorder fields of every supported type, pin fields to the header, and see the ID-card render as designed.
3. A user can upload, download, and delete a document on a person, with metadata shown.
4. A user can search people by name.
5. Data (DB + uploads) survives container recreation, and the backup/restore procedure works as documented.
6. All data routes reject unauthenticated access.
