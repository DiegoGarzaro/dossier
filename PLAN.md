# Dossier — Delivery Plan & Task Tracker

> Living checklist tracking every task from current state to full delivery.
> Legend: `[x]` done · `[~]` partial · `[ ]` pending. "✓ verified" = exercised by a passing test or manual smoke test.
> Source of truth for scope: [Product & Software Requirements](docs/Product%20&%20Software%20Requirements.md) · [Architecture](docs/Architecture.md) · [Design System](docs/Design%20System.md).
>
> **Defects & tech debt live in [`ISSUES.md`](ISSUES.md), not here.** This file tracks planned scope;
> the moment you discover a gap/bug/improvement while coding, log it in `ISSUES.md` with a `G-NN` id.
> Items below may reference those ids (e.g. G-01) for traceability.

**Last assessed:** 2026-07-04

---

## Status at a glance

| Area | State |
|---|---|
| MVP backend (Epics A–D, search, backup) | ✅ implemented & tested (9/9 backend tests, ruff clean) |
| MVP frontend (all screens) | ✅ implemented, type-checks + builds |
| Docker packaging | ✅ built, run, and verified end-to-end (arm64 + amd64) |
| Relationships (Epic E, Phase 2) | 🟡 data model only; no service/API/UI |
| Field-value search, JSON export (Phase 3) | ⬜ not started |
| Multi-user, i18n, OCR, audit (Phase 4) | ⬜ not started |
| Test coverage | 🟡 backend covered; no frontend tests |
| Hardening (rate-limit, proxy flag, fonts) | 🟡 gaps listed below |

---

## MVP — must-have to ship (Epics A, B, C, D + F1 + G1/G2)

### Epic A — Authentication & Access
- [x] First-run admin setup, refuses once initialized (FR-5) — ✓ verified
- [x] Login / logout (FR-3) — ✓ verified
- [x] Password change, revokes other sessions (FR-3) — ✓ verified (backend)
- [x] Argon2id hashing, hash-only storage (FR-2 / SEC-2)
- [x] Server-side sessions, revocable, sliding 14-day expiry (FR-4)
- [x] Auth guard on all data routes → 401 (FR-1 / SEC-1) — ✓ verified
- [x] CSRF double-submit on unsafe methods (SEC-3) — ✓ verified
- [ ] Login rate-limiting / lockout on repeated failures (hardening, not in FR but recommended)
- [ ] Frontend: change-password UI wired to `/api/auth/password` — **DONE in SettingsPage**, needs manual verification

### Epic B — People
- [x] Create person with required name + seeded pinned fields (FR-6/17) — ✓ verified
- [x] ID-card detail payload (FR-7) — ✓ verified
- [x] Rename person (FR-8) — ✓ verified
- [x] Profile photo upload/replace, image-validated (FR-8)
- [x] Delete person, cascades fields/documents/relationships + files (FR-9) — ✓ verified
- [x] People index grid with thumbnails + pinned preview (FR-10)
- [x] Frontend: index, ID-card, add/rename/delete dialogs, photo picker

### Epic C — Fields (core)
- [x] Add unlimited fields (FR-11) — ✓ verified
- [x] Six types: text, textarea, number, date, boolean, sensitive (FR-13)
- [x] Type validation on write (FR-14) — ✓ verified (number/date/boolean)
- [x] Edit label/value/type/pinned (FR-15/16) — ✓ verified
- [x] Remove field (FR-15) — ✓ verified
- [x] Reorder API + bulk position update (FR-15) — ✓ verified
- [x] Pinned fields render in card header with amber rule (FR-16)
- [x] Sensitive values masked by default, reveal-on-demand (SEC-7)
- [x] Drag-and-drop reorder UI — ✓ verified (grip handle + keyboard arrow-key alternative,
      confined to pinned/unpinned groups) — Design System §5.3
- [ ] Inline value edit exists; confirm keyboard/a11y flows

### Epic D — Documents
- [x] Upload PDF/PNG/JPG/WEBP (FR-18) — ✓ verified
- [x] Magic-byte + extension validation, reject mismatch (SEC-6) — ✓ verified
- [x] Random storage filename, metadata in DB (FR-19)
- [x] Configurable max size, streamed with limit (FR-20)
- [x] Download as attachment + nosniff (FR-21 / SEC-6) — ✓ verified
- [x] Delete file + metadata (FR-21) — ✓ verified
- [x] Show type/size/date (FR-D5); upload/download/delete UI
- [ ] **Document rename UI** (PATCH endpoint exists; not surfaced in UI)

### Epic F — Search (MVP subset)
- [x] Search people by name, case-insensitive, ILIKE-escaped (FR-26 / F1) — ✓ verified

### Epic G — Data Safety (MVP subset)
- [x] All persistent data on `/data` volume (FR-28)
- [x] Backup/restore procedure documented (FR-29 / G1/G2) — README
- [x] Manually validate a backup→restore round-trip (acceptance §13.5) — ✓ verified (stop → tar →
      wipe `data/` → untar → start → admin session + data intact)

### MVP packaging & deploy
- [x] Multi-stage Dockerfile (node build → python runtime)
- [x] docker-compose.yml with data volume + env
- [x] Alembic auto-migrate on startup (NFR-8)
- [x] Build the image & run `docker compose up` end-to-end — ✓ verified (also uncovered & fixed a real
      bug, G-17: missing `.dockerignore` let host `.venv`/`node_modules` clobber the image's own)
- [x] Verify amd64 + arm64 build (NFR-1) — ✓ verified (native arm64 + cross-built linux/amd64 via buildx)

---

## MVP definition of done (Acceptance Criteria §13)

- [x] 1. Fresh `docker compose up` → running app + first-run admin setup — ✓ verified
- [x] 2. Create person, add/edit/remove/reorder all 6 field types, pin, card renders — ✓ verified
- [x] 3. Upload/download/delete a document with metadata shown — ✓ verified (API)
- [x] 4. Search people by name — ✓ verified
- [x] 5. Data survives container recreation; backup/restore works as documented — ✓ verified
- [x] 6. All data routes reject unauthenticated access — ✓ verified

---

## Phase 2 — Relationships (Epic E)

- [x] `relationships` table modeled with constraints (self-link, unique pair+type)
- [ ] Repository: create/list-for-person/delete
- [ ] Service: canonicalize `child`→`parent`, inverse-label derivation (FR-23)
- [ ] Service: reject self-links & duplicates (FR-24) — DB enforces; add friendly errors
- [ ] Schemas: RelationshipCreate / RelationshipOut (with resolved direction)
- [ ] Router: `POST /api/relationships`, `DELETE /api/relationships/{id}` (FR-22/25)
- [ ] Include relationships in the person-detail payload
- [ ] Frontend: relationships section — grouped chips, navigable, add/remove (Design System §5.5)
- [ ] Tests: inverse label, self/duplicate rejection, bidirectional display

---

## Phase 3 — Search polish, export/import, settings

- [ ] Field-value search, excluding `sensitive` from plaintext index (FR-27 / F2)
- [ ] `GET /api/search?q=&fields=true` endpoint + UI surfacing matches
- [ ] JSON export of one person / whole dataset (FR-30 / G3)
- [ ] JSON import / restore-from-export
- [ ] Settings polish (backup status, data summary)

---

## Phase 4 — Optional / future

- [ ] Multiple user accounts + roles (revisits D1)
- [ ] Internationalization (externalize copy) (NFR-10)
- [ ] OCR / auto-fill from uploaded IDs (NG5 → future)
- [ ] Audit log

---

## Cross-cutting: quality, security, ops (do alongside phases)

### Testing
- [x] Backend: auth, people, fields, documents flows (9 tests) — ✓ passing
- [ ] Backend: password-change flow, session expiry, photo upload validation
- [ ] Frontend: Vitest + Testing Library — ID-card render, inline edit, pin, sensitive reveal, theme switch
- [ ] End-to-end acceptance checklist mapped to §13
- [ ] CI pipeline: `ruff check`, pytest, eslint, FE build, docker build (Architecture §12)

### Security hardening
- [x] Argon2id, CSRF, HTTP-only SameSite cookies, upload allow-list, nosniff
- [ ] **Consume `DOSSIER_TRUST_PROXY`** — currently declared but unused; wire forwarded-header trust + `Secure` cookies when set (SEC-8)
- [ ] Login rate-limiting (see Epic A)
- [ ] Security review pass before external exposure
- [ ] Document Caddy/reverse-proxy HTTPS example (Architecture §9 / SEC-8)

### Accessibility & polish (NFR-9)
- [x] Labeled inputs, focus-visible ring, keyboard-operable dialogs
- [ ] Skip-to-content link (Design System §5.6)
- [ ] Toast component for success/error (currently inline only) — Design System §5.6
- [ ] Contrast audit of final tokens with a checker
- [ ] Responsive pass on a real phone browser (NFR-5)

### Design system fidelity
- [x] Light/dark semantic tokens, warm-archival palette, theme toggle + persistence
- [ ] **Self-host Source Serif 4 / Inter / IBM Plex Mono as woff2** (currently system fallback; needed for NFR-2 no-CDN + intended type)
- [ ] Field-type badges/icons per Design System §2.4
- [ ] Wordmark/logo asset for "Dossier" (DS-3)

### Repo & housekeeping
- [x] Initialize git repository + initial commit — ✓ verified (`origin` set to github.com/DiegoGarzaro/dossier)
- [ ] Decide whether to rename repo folder `profid` → `dossier`
- [x] `.gitignore` covers data/, venvs, node_modules, built static
- [x] Confirm `uv.lock` + `package-lock.json` committed for reproducible builds — ✓ verified
- [ ] Resolve remaining open decision **D6** (add `select`/`file` field types now vs later)

---

## Defects & tech debt

Tracked in **[`ISSUES.md`](ISSUES.md)** — the running ledger of discovered gaps, bugs, and
improvements (`G-NN` ids). Keep it current as you code; this plan links to those ids where relevant.
