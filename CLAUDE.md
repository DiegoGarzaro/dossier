# CLAUDE.md — Dossier

Guidance for working in this repository. Read this before making changes.

**Dossier** — *"Your people, on file."* A self-hosted, authenticated vault where each person is
an ID-card-style record: pinned fields, unlimited custom fields, uploaded documents, and (Phase 2)
relationships. Single Docker container: FastAPI serves the JSON API **and** the built React SPA.

Planned scope & status live in [`PLAN.md`](PLAN.md); discovered defects & tech debt live in
[`ISSUES.md`](ISSUES.md). Requirements/architecture/design live in [`docs/`](docs/). Keep `PLAN.md`
checkboxes in sync when you complete or add work, and log findings in `ISSUES.md` as you go.

---

## Golden rules

1. **TDD is the default.** Write a failing test first, then the code to pass it. No production
   behaviour lands without a test that would fail if it broke. See "TDD workflow" below.
2. **Security is a requirement, not a feature.** Every change is measured against the SEC rules
   below. When in doubt, choose the safer option and say so.
2a. **Log every gap you find.** The moment you spot a bug, gap, or improvement — even if unrelated
   to the task and even if you fix it immediately — record it in [`ISSUES.md`](ISSUES.md) with a
   `G-NN` id, type, and severity. Never fix silently or rely on memory. (`PLAN.md` = planned scope;
   `ISSUES.md` = defects & tech debt.)
3. **Respect the layering.** `routers → services → repositories → models`. Never skip a layer.
4. **Async all the way.** Async SQLAlchemy, async service/repo methods, `await` everything.
5. **Run the gate before handing back:** `ruff check .` and `pytest` must be green (backend);
   `npm run build` (type-check + build) must pass (frontend).

---

## Architecture & layering

```
routers/       HTTP only: parse request, call one service, shape response. No business logic, no DB.
services/      Business rules, validation, orchestration. The only place decisions are made.
repositories/  All database access. One per aggregate. Returns models; no HTTP concepts.
models/        SQLAlchemy ORM. schemas/ holds Pydantic request/response models.
core/          Cross-cutting: errors, enums, file validation.
```

Rules that keep this clean (SOLID in practice):
- A **router** depends on services via constructor (`Service(db)`); it never touches a repository
  or builds a query.
- A **service** never imports FastAPI/`Request`/`Response` or raises `HTTPException`. It raises
  domain errors from `app/core/errors.py` (`NotFoundError`, `InvalidInputError`, `ConflictError`,
  `AuthenticationError`, `PayloadTooLargeError`); `main.py` maps those to status codes.
- A **repository** never contains business rules — no validation, no cross-entity decisions.
- New aggregate ⇒ add model + schema + repository + service + router, in that order, each with tests.

---

## TDD workflow

Red → Green → Refactor, one behaviour at a time:

1. **Red** — add a test in `backend/tests/` describing the behaviour or bug. Run `pytest` and watch
   it fail for the right reason.
2. **Green** — write the minimum code to pass. Prefer putting logic in a **service** so it can be
   tested without HTTP.
3. **Refactor** — clean up with tests green. Re-run `ruff check .` and `pytest`.

- **Bug fix?** First write a failing regression test that reproduces it, then fix.
- **New endpoint?** Test the service rule *and* the router (auth guard, CSRF, status codes).
- Test **behaviour and edge cases**, not implementation details: validation failures, cascade
  deletes, permission/auth, boundary sizes, inverse-label logic, duplicate/self-link rejection.
- Every test must be able to fail — assert on real outcomes, not just `200`.

### Testing conventions
- `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`); httpx `AsyncClient` via ASGI transport.
- Fixtures in `tests/conftest.py`: `client` (anonymous), `authed_client` (completed setup + CSRF
  header wired). Tests run against an **isolated temp data dir** (`DOSSIER_DATA_DIR` set before app
  import) — never the real `data/`.
- Name tests `test_<behaviour>`; keep them independent and order-free (create then clean up).
- Cover the security surface: unauthenticated → 401, missing/invalid CSRF → 403, upload
  magic-byte mismatch → 400, oversized upload → 413.

---

## Coding patterns

- **Google-style docstrings** on every public function/method, with typed `Args:` and `Returns:`
  (and `Raises:` where a domain error is expected).
- **Type hints everywhere**; modern syntax (`str | None`, `list[X]`). Target Python 3.12.
- **Pydantic v2** for all request/response bodies; validate at the edge (schemas), enforce rules in
  services. Use `model_config = ConfigDict(from_attributes=True)` for ORM-backed responses.
- **Dependency injection** via FastAPI `Depends` (`DbSession`, `CurrentUser`) — don't reach for
  globals. The DB session is request-scoped and commits at the router/service boundary.
- **Small functions, clear names, early returns.** Match the style of surrounding code.
- **Never build SQL by string** — SQLAlchemy expression language only (SEC-5).
- Keep it **stdlib + existing deps**; discuss before adding a dependency. Managed with **uv**.
- Run `ruff check . --fix` to auto-fix; leave the tree lint-clean.

---

## Security rules (SEC-* — non-negotiable)

- **Auth on everything.** All `/api` routes except `/api/auth/*` require `CurrentUser`. Adding a
  route ⇒ it's behind the guard by default; if you make one public, justify it (SEC-1 / FR-1).
- **Passwords:** Argon2id via `app/security.py` only; store hashes, never plaintext; never log
  credentials or session tokens (SEC-2).
- **Sessions:** server-side, revocable, HTTP-only + SameSite cookie; logout and password-change
  invalidate sessions. Don't move auth state into JWTs or localStorage (FR-4).
- **CSRF:** double-submit token enforced on POST/PUT/PATCH/DELETE by middleware. The frontend echoes
  the `dossier_csrf` cookie as `X-CSRF-Token`. Don't exempt state-changing routes (SEC-3).
- **Uploads:** allow-list (PDF/PNG/JPG/WEBP), **sniff magic bytes** (don't trust client
  content-type), enforce size limit while streaming, store under a **random** filename outside any
  executable path, serve as `attachment` + `X-Content-Type-Options: nosniff` (SEC-6).
- **Output:** rely on React's escaping; never `dangerouslySetInnerHTML` with stored field values
  (SEC-4). Store raw, encode on output.
- **Sensitive fields:** masked by default in the UI, revealed only on demand; keep them out of any
  plaintext search index (SEC-7).
- **No outbound network calls with user data** — no telemetry, no font/asset CDNs; self-host fonts
  and icons (SEC-9 / NFR-2).
- **Behind a proxy:** honor forwarded headers and mark cookies `Secure` only when configured; see
  the pending `DOSSIER_TRUST_PROXY` wiring in `PLAN.md` (SEC-8).
- Validate and sanitize **all** external input in services; fail closed with a domain error.

---

## Conventions you must not silently change

- Env var prefix **`DOSSIER_`** (config, Docker, compose, tests).
- Cookie names **`dossier_session`** / **`dossier_csrf`**; theme key **`dossier-theme`**.
- Password hashing and token generation go through **`app/security.py`**.
- Migrations are **Alembic**, run automatically on startup; generate a migration for every model
  change (`uv run alembic revision --autogenerate -m "..."`) and review it before committing.

---

## Frontend conventions (`frontend/`)

- React 18 + Vite + **TypeScript strict** + Tailwind v4. Build outputs to `backend/app/static`.
- **Design tokens are the source of truth** (`src/theme/tokens.css`). Use semantic utilities
  (`bg-surface`, `text-ink`, `border-border`, `text-accent`) so light/dark switch automatically.
  Don't hardcode hex values in components. Follow [`docs/Design System.md`](docs/Design%20System.md).
- Server state via **TanStack Query**; all requests go through `src/lib/api.ts` (adds the CSRF
  header, throws typed `ApiError`). Don't call `fetch` directly in components.
- Accessibility: labeled inputs, `aria-label` on icon buttons, keyboard-operable dialogs, visible
  focus ring (NFR-9).
- New user-facing behaviour should get a Vitest + Testing Library test (see `PLAN.md` — frontend
  test setup is pending; add it when you touch this).

---

## Commands

```bash
# Backend (from backend/)
uv sync                                   # install deps
uv run uvicorn app.main:app --reload      # dev server → http://localhost:8000
uv run ruff check .                       # lint (must pass)
uv run ruff check . --fix                 # auto-fix
uv run pytest                             # tests (must pass)
uv run alembic revision --autogenerate -m "msg"   # new migration after model change

# Frontend (from frontend/)
npm install
npm run dev                               # dev server (proxies /api) → http://localhost:5173
npm run build                             # type-check + build into backend/app/static

# Full app / production-style
docker compose up -d                      # → http://localhost:8080
```

## Definition of done for a change

- [ ] A test was written first and fails without the change.
- [ ] `ruff check .` and `pytest` are green; `npm run build` passes if frontend touched.
- [ ] Security rules above are upheld (auth, CSRF, validation, no secrets logged).
- [ ] Docstrings + types added; layering respected.
- [ ] `PLAN.md` task checked off; **any newly discovered gap/bug logged in [`ISSUES.md`](ISSUES.md)**;
      migration generated if models changed.
