# Dossier — Issue & Tech-Debt Ledger

> Master ledger of every **gap, bug, or improvement** discovered while building Dossier.
> This is the source of truth for defects and debt; forward-looking scope/tasks live in [`PLAN.md`](PLAN.md).

**Working agreement:** the moment something is discovered — even if unrelated to the current task,
even if fixed immediately — it gets a row here. Never fix silently or rely on memory.

- **Type:** `Bug` (broken behaviour) · `Gap` (missing but planned) · `Improve` (works, could be better)
- **Severity:** 🔴 high · 🟠 med · 🟡 low
- **Status:** `open` · `in progress` · `done (YYYY-MM-DD)`
- **Ids** are stable: append as `G-NN`, never renumber or reuse. Close an item by setting its status to `done` (keep the row for history).

**Last updated:** 2026-07-04 (rev 2)

---

## Open & in progress

| ID | Type | Sev | Area | Finding & intended action | Status |
|---|---|---|---|---|---|
| G-01 | Gap | 🟠 | Fields UI | Drag-and-drop reorder not built (reorder API + test exist). Build DnD in the ID-card field list. | open |
| G-02 | Gap | 🟡 | Documents UI | Document rename not surfaced (PATCH endpoint exists). Add inline rename. | open |
| G-04 | Gap | 🟠 | Testing | No frontend tests. Stand up Vitest + Testing Library, then cover ID-card render, inline edit, pin, sensitive reveal, theme switch. | open |
| G-05 | Gap | 🟡 | Design/privacy | Fonts fall back to system stacks; ship self-hosted woff2 (Source Serif 4 / Inter / IBM Plex Mono) for NFR-2 no-CDN + intended type. | open |
| G-06 | Gap | 🟠 | Deploy | Docker image never built/run end-to-end. Build + `docker compose up`, verify acceptance §13.1/§13.5. | open |
| G-07 | Gap | 🟠 | Security | No login rate-limiting / lockout on repeated failures. Add throttling. | open |
| G-08 | Gap | 🟠 | Repo | Project is not under version control. `git init` + initial commit; confirm lockfiles committed. | open |
| G-16 | Gap | 🟠 | Search/privacy | When field-value search (Phase 3 / FR-27) is built, **exclude `sensitive` values** from any plaintext index (SEC-7). Tracking so it isn't missed. | open |

## Resolved

| ID | Type | Sev | Area | Finding & intended action | Status |
|---|---|---|---|---|---|
| G-03 | Gap | 🟠 | Security/ops | `DOSSIER_TRUST_PROXY` declared but never consumed. Wired: `secure = settings.trust_proxy or request.url.scheme == "https"` in `auth.py` and `middleware.py`. | done (2026-07-04) |
| G-09 | Bug | 🟡 | People UI | Index-grid thumbnail URL had no cache-bust → stale photo after change. Fixed: added `updated_at` to `PersonSummary` schema + `?v=<updated_at>` param on grid photo URLs. | done (2026-07-04) |
| G-10 | Gap | 🟠 | Auth/DB | Expired `sessions` rows never purged → unbounded table growth. Fixed: `SessionRepository.purge_expired()` called in app `lifespan` on startup. | done (2026-07-04) |
| G-11 | Improve | 🟡 | Security | Photo/document `FileResponse`s had no `Cache-Control`. Fixed: added `Cache-Control: private, no-store` to both photo and document download responses. | done (2026-07-04) |
| G-12 | Improve | 🟡 | Validation | Field `value` had no length cap. Fixed: `max_length=10_000` added to `FieldCreate.value` and `FieldUpdate.value` in `schemas/field.py`. | done (2026-07-04) |
| G-13 | Improve | 🟠 | Frontend | No React error boundary. Fixed: `ErrorBoundary` class component added to `ui.tsx`, wraps the entire app in `main.tsx`. | done (2026-07-04) |
| G-14 | Improve | 🟡 | Ops | `/api/system/health` returned ok without checking DB. Fixed: endpoint now runs `SELECT 1` via `DbSession` dependency. | done (2026-07-04) |
| G-15 | Improve | 🟡 | Validation | `float()` accepts `inf`/`nan` in number-field validation. Fixed: `math.isfinite()` check added after parse in `field_service.py`. | done (2026-07-04) |
