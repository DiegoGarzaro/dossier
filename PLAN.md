# Dossier — Delivery Plan & Task Tracker

> Living checklist tracking every task from current state to full delivery.
> Legend: `[x]` done · `[~]` partial · `[ ]` pending. "✓ verified" = exercised by a passing test or manual smoke test.
> Source of truth for scope: [Product & Software Requirements](docs/Product%20&%20Software%20Requirements.md) · [Architecture](docs/Architecture.md) · [Design System](docs/Design%20System.md).
>
> **Defects & tech debt live in [`ISSUES.md`](ISSUES.md), not here.** This file tracks planned scope;
> the moment you discover a gap/bug/improvement while coding, log it in `ISSUES.md` with a `G-NN` id.
> Items below may reference those ids (e.g. G-01) for traceability.

**Last assessed:** 2026-07-31

---

## Status at a glance

| Area | State |
|---|---|
| MVP backend (Epics A–D, search, backup) | ✅ implemented & tested (31/31 backend tests, ruff clean) |
| MVP frontend (all screens) | ✅ implemented, type-checks + builds |
| Docker packaging | ✅ built, run, and verified end-to-end (arm64 + amd64) |
| Relationships (Epic E, Phase 2) | ✅ implemented end-to-end, backend + frontend, ✓ verified |
| People relationship tree view (Phase 2b, new idea) | ✅ implemented end-to-end, ✓ verified |
| Field-value search, JSON export, vCard export (Phase 3) | ✅ done, ✓ verified |
| JSON import / restore (Phase 3) | ✅ done, ✓ verified |
| Encrypted backup, tags/favorites, settings polish (Phase 3) | ⬜ not started |
| Multi-user + per-user data, admin panel, audit, Postgres (Phase 4 epic) | ⏳ deferred until app is very mature; scoped 2026-07-06 |
| Test coverage | 🟡 backend covered; frontend Vitest set up (tree-layout unit tests only so far) |
| Hardening (rate-limit, proxy flag, fonts) | 🟡 rate-limit + proxy flag done; fonts still gap (G-05) |

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
- [x] Login rate-limiting / lockout on repeated failures — ✓ verified (locks after
      `DOSSIER_LOGIN_MAX_ATTEMPTS` failures for `DOSSIER_LOGIN_LOCKOUT_MINUTES`)
- [ ] Frontend: change-password UI wired to `/api/auth/password` — **DONE in SettingsPage**, needs manual verification

### Epic B — People
- [x] Create person with required name + seeded pinned fields (FR-6/17) — ✓ verified
- [x] **Date of birth as a fixed field** (user request 2026-07-31, extends FR-17's example list) —
      ✓ verified. Seeded as a pinned **system** field of type `date` (so FR-14 validation applies),
      sitting between Document number and Address. Data migration `4c0b49a25546` backfills every
      existing person, inserting it at position 1 and shifting the rest down so the order the user
      arranged is preserved; verified up *and* down against a database seeded with the old layout.
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
- [x] Document rename UI — ✓ verified

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
- [x] Repository: create/list-for-person/delete — ✓ verified
- [x] Service: canonicalize `child`→`parent`, inverse-label derivation (FR-23) — ✓ verified
- [x] Service: reject self-links & duplicates (FR-24) — friendly 400/409, both stored orders checked
- [x] Schemas: RelationshipCreate / RelationshipOut (with resolved direction) — ✓ verified
- [x] Router: `POST /api/relationships`, `DELETE /api/relationships/{id}` (FR-22/25) — ✓ verified
- [x] Include relationships in the person-detail payload — ✓ verified
- [x] Frontend: relationships section — grouped chips, navigable, add/remove (Design System §5.5) — ✓ verified
- [x] Tests: inverse label, self/duplicate rejection, bidirectional display — ✓ verified (8 new tests)

---

## Phase 2b — People relationship tree view (new idea)

> Not in the original requirements docs — user idea, added 2026-07-05. Builds directly on Epic E's
> relationship data; view-only, no editing from this screen. Not a strict ancestry-only genealogy
> chart — it visualizes every relationship type (spouse, parent/child, sibling, custom) as one
> connected graph centered on a person.

- [x] Decide traversal scope — full connected component via BFS, clamped to ±3 generations and
      100 nodes (generous for a family vault, bounded for safety)
- [x] Backend: `GET /api/people/{id}/tree` walks the graph into nodes (with relative generation)
      + edges — ✓ verified (5 new tests)
- [x] Frontend: read-only `/people/{id}/tree` route — generation rows with ledger-margin labels
      (Grandparents / Parents / This generation / …), SVG connectors drawn from measured node
      positions, amber seal ring on the center person — ✓ verified live
- [x] Non-hierarchical cases: spouse/sibling/custom stay in the same generation row (solid tie /
      dashed / dotted lines per kind, legend shown); parent links draw generational elbows; on
      conflicting paths BFS first-assignment wins (it's a view, not a validator)
- [x] Nodes link back to each person's ID-card — ✓ verified (entry point: "View tree" in the
      Relationships section)

### Richer categories & kinship captions (G-31, treemich-inspired, added 2026-07-06)

- [x] More relationship categories: partner, friend, colleague, godparent/godchild (godchild
      canonicalizes to a godparent row like child→parent; godparent shifts a generation) —
      ✓ verified (4 new tests)
- [x] Gendered roles on links (`related_role`: mother/father/son/daughter/brother/sister/
      husband/wife/god-*) — the role labels the counterpart on cards ("Mother" instead of
      "Parent") and must refine its structural type or the API 400s — ✓ verified
- [x] Derived kinship captions in the tree: each node names its relationship to the center
      person ("Mother of X", "Grandmother of X", "Uncle of X", "Cousin of X", in-law/step
      terms), computed from the BFS path and gendered by recorded roles — ✓ verified live
- [x] vCard RELATED TYPE mapping extended to role labels and the new categories (RFC 6350 §6.6.6)
- [x] Genealogy layout engine (G-32): couples clustered as units, barycenter row ordering,
      parents centered over children, no row wrapping (horizontal scroll), family "bus"
      connectors with staggered rails, sibling ties suppressed when a shared parent already
      joins the pair — pure `treeLayout.ts` module, 7 Vitest unit tests — ✓ verified live
      (Playwright, replica of the reported messy tree)
- [x] Structurally-stable generations (G-32/G-33): blood/marriage edges lay the generation
      ladder first, godparent/social edges only place otherwise-unreached people, so the tree
      reads identically from any viewer (highlight + captions change, structure doesn't) and a
      godparent-who-is-also-a-grandparent keeps their blood generation. Redundant soft ties
      (already blood-connected) dropped in layout. 4 new tests — ✓ verified live across 3 views

---

## Phase 3 — Search polish, export/import, settings

- [x] Field-value search, excluding `sensitive` from plaintext index (FR-27 / F2, closes G-16) —
      ✓ verified. Extended `GET /api/people?q=&fields=true` (chosen over a separate `/api/search`
      endpoint to reuse the index grid): correlated `EXISTS` over non-sensitive field values only,
      LIKE-escaped substring, case-insensitive. `PersonSummary.matched_fields` surfaces which field
      matched so the card shows why the person appeared; the index has a "Search field values too"
      toggle. Sensitive values are never indexed nor surfaced. 3 new backend tests (off-by-default,
      match+surface, sensitive-excluded) + live Playwright + curl SEC-7 check.
- [x] JSON export of one person / whole dataset (FR-30 / G3, closes G-34) — ✓ verified.
      `GET /api/people/{id}/export` and `GET /api/export` return one versioned envelope
      (`schema_version`, `exported_at`, `scope`, `includes_sensitive_values`, `people`,
      `relationships`) so a future importer learns a single shape. **`sensitive` field values are
      withheld by default** (`value: null` + `value_omitted: true`, keeping the field's shape) and
      only travel with an explicit `?include_sensitive=true` (SEC-7). Documents export as metadata
      only — never the on-disk random filename (SEC-6) and never the bytes, which stay on `/data`.
      Relationships export in their stored canonical direction with both names denormalized.
      UI: "Export JSON" on the ID-card next to the vCard link, and a dataset export in Settings →
      Backups with an opt-in "Include sensitive field values" checkbox + plaintext warning.
      9 new backend tests + live curl round-trip (headers, sensitive withheld/opted-in, 401 anon).
- [x] JSON import / restore-from-export (closes G-38) — ✓ verified. `POST /api/import` takes the
      export envelope back. **Decisions taken:** import is *additive and never destructive* (merge,
      not replace) — nothing is deleted, renamed, or overwritten; people are matched by **exact
      name** and an existing match is skipped with its links reconnected to the stored record, so
      re-running the same file is a no-op instead of a way to duplicate the vault. `value_omitted`
      fields import blank and are counted in the report — a withheld secret can never null out a
      stored one. Field values are validated against their type before anything is written, so a
      tampered file is refused whole (the request transaction rolls back). Documents are reported
      as unrestorable (metadata only, see G-36). Returns an `ImportReport` the UI renders.
      11 new backend tests + live export→wipe→import→re-import round-trip.
- [ ] Settings polish (backup status, data summary)
- [x] **vCard export for a person** (new idea, alongside JSON export FR-30) — ✓ verified.
      `GET /api/people/{id}/vcard` (vCard 4.0). Field-mapping: label containing "email"/"phone"
      → EMAIL/TEL, exact "Address" → ADR, everything else (non-sensitive, non-empty) → NOTE line;
      `sensitive`-type values are always excluded (SEC-7). Relationships included as RELATED lines
      with a TYPE param for the four standard types. "Export vCard" link on the ID-card. Deliberately
      skips PHOTO embedding and RFC 6350 line-folding for >75-octet lines — both are follow-ups if
      needed, not required for a useful, parseable file. 7 new tests.
- [ ] **Encrypted backup/restore** (new idea, added 2026-07-05): in-app export produces a
      passphrase-encrypted archive; restore decrypts before applying. Goes beyond the current
      plain-tar procedure (G1/G2, README) — needs a decision on encryption approach (e.g. age/gpg
      symmetric vs. in-app AES-GCM) and confirmation the passphrase is never persisted server-side

### Organizing people — tags & favorites (user idea, added 2026-07-07)

> **Recommendation: tags (many-to-many) + a favorite star — not rigid "books."** A book forces
> each person into one bucket, but people cross categories (a cousin who's also a colleague), so
> tags are strictly more flexible: a tag named "Family"/"School" gives the same grouping while
> allowing overlap, and books are just tags with exclusive membership. Isolated "books" as separate
> namespaces overlap with the Phase 4 multi-user/per-user-data work, so don't build a parallel
> concept — revisit only if true walled-off address books are wanted.

- [ ] **Tags aggregate** (new Tag model + schema + repo + service + router, per layering): create/
      rename/delete/list tags; a `person_tags` many-to-many join with cascade on person/tag delete.
- [ ] Assign/unassign tags on the ID-card (chip UI, create-on-type); a person can hold many tags.
- [ ] Filter the people index by one or more tags — extend the existing `GET /api/people` (add a
      `tags=` filter alongside `q`/`fields`) so search + tag filter compose; show active tag chips.
- [ ] **Favorite star**: `is_favorite` boolean on Person (model + migration), toggle on card/grid,
      filter + sort favorites to the top of the index. Small, complementary to tags — do both.
- [ ] Tests: tag CRUD + uniqueness, many-to-many assignment, cascade on delete, index filter by
      tag (AND vs OR semantics — decide, default OR), favorite toggle + filter.

---

## Phase 4 — Multi-user, audit, admin, database (user ideas, added 2026-07-06)

> **⏳ Deferred: do not start until the app is very mature.** Per the user (2026-07-07), this
> whole epic is a "someday" reshaping of the product, gated on the single-user app being polished
> and battle-tested first — not near-term work. Kept here fully scoped so the direction isn't lost.
>
> These four are interdependent and reshape the data model, so treat them as one epic
> sequenced roughly in this order: **(1) database migration → (2) multi-user + per-user data →
> (3) admin panel → (4) audit log.** Each is a security boundary (SEC-1/SEC-7 in spirit), so
> every step needs tests proving one user cannot see or touch another's data. None started.

### 4a — Move off SQLite to a server database
- [ ] **Decision: PostgreSQL** (recommended over MariaDB/MySQL for this app). Rationale:
      the stack is already async SQLAlchemy + Alembic, and Postgres has the most mature async
      driver (`asyncpg`) and the best-tested SQLAlchemy async path; native `JSONB`, partial
      indexes, and `citext`/`ILIKE` suit the custom-field + case-insensitive name search we
      already do; row-level constraints and `gen_random_uuid()` help the per-user ownership work
      below. MariaDB is viable but its async drivers (`asyncmy`/`aiomysql`) are less polished and
      it has collation/`utf8mb4` and DDL-in-transaction quirks that complicate Alembic.
- [ ] Reality check first: **SQLite (WAL mode) likely still suffices** at family-vault scale and
      low write concurrency — moving is mostly about "a real server DB" and concurrent multi-user
      writes, not a current bottleneck. Confirm the driver (Postgres) is worth the ops cost before
      committing.
- [ ] Keep the repository layer DB-agnostic (no raw SQL, SEC-5) so the swap is config + driver +
      compose service; parameterize via `DOSSIER_DATABASE_URL`, default still SQLite for dev/tests.
- [ ] Alembic: verify every existing migration runs on Postgres (batch-alter ops used for SQLite
      may need review); add a Postgres service to `docker-compose.yml` with its own volume.
- [ ] Tests must run against both engines (or at least Postgres in CI) — the temp-dir SQLite
      fixture stays for fast local runs.

### 4b — Multiple users, each with their own people & tree
- [ ] Users table already exists (single admin today); extend to real multi-account signup/invite.
- [ ] **Per-user data ownership:** add `owner_id` (FK → users) to `people` (documents, fields, and
      relationships inherit ownership through their person). Every people/field/document/
      relationship/tree/vCard query filters by the current user — enforced in the **service** layer,
      not just the router, and covered by tests that a second user gets 404/empty, never another
      user's rows. This is the core security boundary (extends SEC-1).
- [ ] Relationships stay within one owner's graph (no cross-user links in v1) — the tree walk and
      kinship derivation already operate per connected component, so scoping is a `WHERE owner_id`.
- [ ] Decide sharing model (probably none in v1: strictly private per user, matching the
      "self-hosted personal vault" framing) and record the decision.
- [ ] Session/CSRF model is unchanged (already server-side, per-user) — just associate data.

### 4c — Admin panel for user administration
- [ ] Roles: `admin` vs `user` on the users table (first-run setup user becomes `admin`).
- [ ] Admin-only routes (behind `CurrentUser` **and** a role check, fail-closed): list users,
      create/invite, deactivate/lock, reset password, delete user (cascades their data), see
      last-login/lockout state (reuses the existing lockout fields).
- [ ] Admin **cannot** read another user's people/documents (accountability without surveillance) —
      admin manages accounts, not contents; assert this in tests. Revisit only if a deliberate
      "shared vault" feature is chosen.
- [ ] Frontend: `/admin` section (hidden for non-admins), user table with the above actions,
      guarded client-side *and* server-side.

### 4d — Audit log (history & change tracking)
- [ ] Append-only `audit_events` table: who (user_id), when (utc), what (action enum:
      create/update/delete/login/failed-login/export/download), target (entity type + id), and a
      compact JSON diff of changed fields. **Never log `sensitive`-type field values or credentials/
      tokens** (SEC-2/SEC-7) — store field *names* changed, not secret values.
- [ ] Write from the service layer (the only place decisions are made) so every mutating path is
      covered; consider a small helper/decorator to avoid per-endpoint boilerplate.
- [ ] Read surface: per-person "history" view and (admin) a global event feed; both filtered by
      ownership. Retention/rotation policy decision noted.
- [ ] Tests: a create/edit/delete round-trip produces the expected events; sensitive values are
      absent from the audit payload (regression guard, like G-30).

### Deferred / not part of this epic
- [ ] Internationalization (externalize copy) (NFR-10)
- [ ] OCR / auto-fill from uploaded IDs (NG5 → future)

---

## Cross-cutting: quality, security, ops (do alongside phases)

### Testing
- [x] Backend: auth, people, fields, documents, relationships, vcard, tree, kinship, export,
      import flows (74 tests) — ✓ passing
- [x] Frontend: Vitest set up (`npm run test`); tree-layout engine unit tests (9) — ✓ passing
- [ ] Backend: password-change flow, session expiry, photo upload validation
- [ ] Frontend: Vitest + Testing Library — ID-card render, inline edit, pin, sensitive reveal, theme switch
- [ ] End-to-end acceptance checklist mapped to §13
- [ ] CI pipeline: `ruff check`, pytest, eslint, FE build, docker build (Architecture §12)

### Security hardening
- [x] Argon2id, CSRF, HTTP-only SameSite cookies, upload allow-list, nosniff
- [x] Consume `DOSSIER_TRUST_PROXY` — wired in `auth.py`/`middleware.py` (G-03, SEC-8)
- [x] Login rate-limiting (see Epic A, G-07)
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
