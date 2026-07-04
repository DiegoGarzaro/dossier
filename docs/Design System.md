# Dossier — Design System

> **Status:** Draft v1.0 — companion to *Product & Software Requirements.md*.
> **Direction:** *Warm archival paper.* The app should feel like a tidy official document / private archive — warm off-white "paper", warm ink, a deep-teal accent, an amber "seal" accent for emphasis. Content dominates; chrome recedes.
> **Modes:** Light and dark defined from the start via semantic tokens.

This document defines the visual language: color tokens (light + dark), typography, spacing, radii, elevation, and the specs for the core components — above all the **ID-card**.

---

## 1. Design principles

1. **Document, not form dump.** The person view should read like a clean identity document: strong name, a few pinned facts, then an orderly list. Generous whitespace, hairline rules, restrained color.
2. **Content is the color.** The palette is mostly warm neutrals. Accent (teal) is used sparingly — interactive elements, focus, the active state. Amber is reserved for "seal"-level emphasis (pinned markers, warnings), never body chrome.
3. **Legibility first.** High contrast for text (WCAG AA minimum, AAA for body where feasible). Document numbers, dates, and codes are set in monospace so digits align and scan like an ID card.
4. **Calm motion.** Transitions are short (120–200ms), easing `ease-out`. No bounce, no decorative animation.
5. **One accent, used with intent.** If everything is highlighted, nothing is. Teal marks "you can act here"; amber marks "pay attention".

---

## 2. Color tokens

Two layers:
- **Primitive tokens** — raw hex values (`--paper-100`, `--teal-600`…). Not used directly in components.
- **Semantic tokens** — role-based (`--bg`, `--surface`, `--text`, `--accent`…). Components reference **only** these, so light/dark is a single swap.

### 2.1 Primitive palette

| Token | Hex | Note |
|---|---|---|
| `--paper-50` | `#FBFAF7` | lightest warm surface tint |
| `--paper-100` | `#F6F4EF` | **base paper** (light bg) |
| `--paper-200` | `#EEEAE1` | subtle raised / hover |
| `--line-200` | `#E7E2D9` | hairline border (light) |
| `--ink-900` | `#1C1917` | **warm ink** (primary text, light) |
| `--stone-600` | `#78716C` | muted text (light) |
| `--stone-400` | `#A8A29E` | tertiary / placeholder |
| `--teal-800` | `#0B5A54` | accent active |
| `--teal-700` | `#0E6B63` | accent hover |
| `--teal-600` | `#0F766E` | **accent** (light) |
| `--teal-300` | `#5EEAD4` | accent (dark mode) |
| `--teal-100` | `#D7EAE7` | accent soft fill (light) |
| `--amber-700` | `#B45309` | **seal accent** (light) |
| `--amber-500` | `#F59E0B` | seal accent (dark) |
| `--amber-100` | `#F7ECD9` | seal soft fill (light) |
| `--red-700` | `#B91C1C` | danger (light) |
| `--red-400` | `#F87171` | danger (dark) |
| `--green-700` | `#15803D` | success (light) |
| `--green-400` | `#4ADE80` | success (dark) |
| `--warmblack-950` | `#1A1815` | base bg (dark) |
| `--warmblack-900` | `#232019` | surface (dark) |
| `--warmblack-800` | `#2B2721` | raised (dark) |
| `--warmblack-700` | `#38332B` | hairline (dark) |
| `--warmwhite-50` | `#F5F1E8` | primary text (dark) |

### 2.2 Semantic tokens — Light

| Semantic | Value | Used for |
|---|---|---|
| `--bg` | `--paper-100` `#F6F4EF` | app background |
| `--surface` | `#FFFFFF` | cards, panels, inputs |
| `--surface-subtle` | `--paper-50` `#FBFAF7` | zebra rows, inset areas |
| `--surface-hover` | `--paper-200` `#EEEAE1` | hover on list rows |
| `--border` | `--line-200` `#E7E2D9` | hairlines, dividers, input borders |
| `--border-strong` | `#D6CFC2` | emphasized separators |
| `--text` | `--ink-900` `#1C1917` | primary text |
| `--text-muted` | `--stone-600` `#78716C` | labels, secondary |
| `--text-subtle` | `--stone-400` `#A8A29E` | placeholder, meta |
| `--accent` | `--teal-600` `#0F766E` | buttons, links, active |
| `--accent-hover` | `--teal-700` `#0E6B63` | hover |
| `--accent-active` | `--teal-800` `#0B5A54` | pressed |
| `--accent-fill` | `--teal-100` `#D7EAE7` | soft accent background |
| `--accent-on` | `#FFFFFF` | text/icon on accent |
| `--seal` | `--amber-700` `#B45309` | pinned marker, emphasis |
| `--seal-fill` | `--amber-100` `#F7ECD9` | pinned chip background |
| `--danger` | `--red-700` `#B91C1C` | destructive actions, errors |
| `--success` | `--green-700` `#15803D` | confirmations |
| `--focus-ring` | `#0F766E` @ 45% | focus outline color |

### 2.3 Semantic tokens — Dark

| Semantic | Value | Used for |
|---|---|---|
| `--bg` | `--warmblack-950` `#1A1815` | app background |
| `--surface` | `--warmblack-900` `#232019` | cards, panels, inputs |
| `--surface-subtle` | `#1F1C17` | zebra rows, inset |
| `--surface-hover` | `--warmblack-800` `#2B2721` | hover |
| `--border` | `--warmblack-700` `#38332B` | hairlines, dividers |
| `--border-strong` | `#4A443A` | emphasized separators |
| `--text` | `--warmwhite-50` `#F5F1E8` | primary text |
| `--text-muted` | `#A8A096` | labels, secondary |
| `--text-subtle` | `#78716C` | placeholder, meta |
| `--accent` | `--teal-300` `#5EEAD4` | buttons, links, active |
| `--accent-hover` | `#7DF0DE` | hover |
| `--accent-active` | `#3FD8C4` | pressed |
| `--accent-fill` | `#123C39` | soft accent background |
| `--accent-on` | `#0A2622` | text/icon on accent (dark teal buttons use dark text) |
| `--seal` | `--amber-500` `#F59E0B` | pinned marker, emphasis |
| `--seal-fill` | `#3A2E15` | pinned chip background |
| `--danger` | `--red-400` `#F87171` | destructive, errors |
| `--success` | `--green-400` `#4ADE80` | confirmations |
| `--focus-ring` | `#5EEAD4` @ 55% | focus outline color |

> **Contrast check (light):** ink `#1C1917` on paper `#F6F4EF` ≈ 14.8:1 (AAA). Teal `#0F766E` on white ≈ 4.9:1 (AA for text, AA-large for UI). Muted `#78716C` on white ≈ 4.6:1 (AA). Amber `#B45309` on white ≈ 4.7:1 (AA). Verify final values with a checker before ship (NFR-9).

### 2.4 Field-type accent map

Each of the six field types (FR-13) gets a small type badge. Keep them monochrome + one hue so they read as metadata, not decoration.

| Field type | Icon (lucide) | Badge tint |
|---|---|---|
| `text` | `type` | neutral (`--text-muted`) |
| `textarea` | `align-left` | neutral |
| `number` | `hash` | neutral |
| `date` | `calendar` | neutral |
| `boolean` | `toggle-left` | `--accent` |
| `sensitive` | `eye-off` | `--seal` |

---

## 3. Typography

Archival/official character comes from pairing a **restrained serif** for identity (person names, section titles) with a **clean sans** for UI, and a **mono** for codes/numbers.

| Role | Family | Fallback stack |
|---|---|---|
| **Display / names** | **Source Serif 4** | `"Source Serif 4", Georgia, "Times New Roman", serif` |
| **UI / body** | **Inter** | `Inter, -apple-system, "Segoe UI", Roboto, sans-serif` |
| **Mono / codes** | **IBM Plex Mono** | `"IBM Plex Mono", "SFMono-Regular", Menlo, monospace` |

> Alternative expressive display face: **Fraunces** (more character, optical sizing) if the app should feel warmer/less corporate. Source Serif 4 is the safe, "official" default. All three families are open-source and self-hosted — no outbound font CDN (NFR-2 / SEC-9).

**Mono is used for:** document numbers, ID codes, dates, `number`-type values, and `sensitive` values (masked). This is the ID-card cue.

### Type scale (1.200 minor-third, 16px base)

| Token | Size / line | Weight | Usage |
|---|---|---|---|
| `display` | 34 / 40px | 600 serif | person name on ID-card header |
| `h1` | 28 / 34px | 600 serif | page titles |
| `h2` | 22 / 28px | 600 serif | section headings (Fields, Documents…) |
| `h3` | 18 / 24px | 600 sans | sub-sections, card titles in grid |
| `body` | 16 / 24px | 400 sans | values, general text |
| `body-sm` | 14 / 20px | 400 sans | field labels, table cells |
| `label` | 12.5 / 16px | 600 sans, +0.04em, uppercase | field labels, meta captions |
| `mono` | 15 / 22px | 500 mono | codes, numbers, sensitive |

**Rules:** labels are `label` style (small caps feel) in `--text-muted`; values are `body`/`mono` in `--text`. Never bold a label and its value together.

---

## 4. Spacing, radius, elevation

**Spacing scale (4px base):** `4, 8, 12, 16, 20, 24, 32, 40, 48, 64`. Tokens `--space-1`…`--space-10`. Card internal padding: 24 (desktop) / 16 (mobile). Section gap: 32.

**Radius:** `--radius-sm 6px` (inputs, badges), `--radius-md 10px` (buttons, rows), `--radius-lg 14px` (cards/panels), `--radius-full 999px` (avatar, chips). Archival = gently rounded, not pill-heavy.

**Elevation (light):** paper feel — shadows are soft and low.
- `--shadow-sm`: `0 1px 2px rgba(28,25,23,.06)`
- `--shadow-md`: `0 2px 8px rgba(28,25,23,.08)`
- `--shadow-lg`: `0 8px 24px rgba(28,25,23,.10)`

**Elevation (dark):** prefer border + subtle lift over shadow; use `--surface`/`--surface-hover` steps and `--border` to separate. Shadows: same offsets at `rgba(0,0,0,.4)`.

**Borders:** default hairline `1px solid var(--border)`. The ID-card uses a `1px` border **plus** `--shadow-md` in light mode to read as a physical card.

---

## 5. Core components

### 5.1 Buttons

| Variant | Light | Behavior |
|---|---|---|
| **Primary** | bg `--accent`, text `--accent-on`, `--radius-md` | hover `--accent-hover`, active `--accent-active`, focus ring |
| **Secondary** | bg `--surface`, text `--text`, border `--border` | hover bg `--surface-hover` |
| **Ghost** | transparent, text `--text-muted` | hover bg `--surface-hover`, text `--text` |
| **Danger** | text `--danger`, border `--danger` (ghost by default; solid on confirm dialogs) | used for delete |

Sizes: `sm` 32px, `md` 40px (default), `lg` 44px. Icon + label spacing 8px. Min touch target 44px on mobile.

### 5.2 Inputs & fields

- Height 40px (`sm` 32), padding 12px, `--radius-sm`, border `--border`, bg `--surface`.
- Focus: 2px `--focus-ring` outline (offset 1px), border → `--accent`.
- Label above input in `label` style. Error text `--danger`, 12.5px, below.
- `textarea`: min 3 rows, auto-grow. `date`: native picker, value displayed in mono. `boolean`: toggle switch (accent when on). `sensitive`: value masked `••••••••` with an eye toggle (`--seal` icon) to reveal; reveal is per-view, never persisted.

### 5.3 The ID-card (the centerpiece)

Layout — desktop:

```
┌──────────────────────────────────────────────────────────────┐
│  ┌────────┐   Diego Garzaro                        [Edit] [⋯] │  ← header
│  │ photo  │   ‹display, serif›                                │
│  │ 96px   │                                                   │
│  │ ○      │   ⌾ PINNED CHIPS (amber marker):                  │
│  └────────┘   │ DOCUMENT №  12.345.678-9  (mono)            │ │
│               │ ADDRESS     Rua X, 100 — City               │ │
│               │ NATIONALITY Brazilian                       │ │
├──────────────────────────────────────────────────────────────┤
│  FIELDS                                        [+ Add field] │  ← section
│  ── label ─────────────  value ───────────────────  ⇅  ✎  ✕ │  ← field row
│  BLOOD TYPE              O+                          ⇅  ✎  ✕ │
│  INSURANCE №             778-221-004  (mono)         ⇅  ✎  ✕ │
├──────────────────────────────────────────────────────────────┤
│  DOCUMENTS                                     [+ Upload]     │
│  📄 Passport.pdf   PDF · 1.2 MB · 2026-02-11   [↓] [🗑]      │
├──────────────────────────────────────────────────────────────┤
│  RELATIONSHIPS (Phase 2)                       [+ Link]      │
│  Spouse:  Ana Garzaro →     Children:  Leo →  Mia →         │
└──────────────────────────────────────────────────────────────┘
```

Specs:
- **Card container:** `--surface`, `--radius-lg`, border `--border`, `--shadow-md`, max-width 880px, centered.
- **Header:** photo (96px `--radius-full`, or placeholder = initials on `--accent-fill`); name in `display`; pinned fields as a stacked list of **pinned chips**. A pinned chip = small `--seal` dot/pin icon + `label`-style key + value; background `--seal-fill` is optional (keep it subtle — a left amber rule reads more "official" than a filled chip).
- **Field row:** grid `label (min 160px) | value (fill) | actions`. Zebra with `--surface-subtle`. Hover reveals `⇅` drag handle, `✎` edit, `✕` remove (icons `--text-subtle` → `--text` on hover; remove → `--danger`). Reorder via drag handle (FR-15 / C5). Inline edit: value becomes an input in place.
- **Pinned toggle:** a pin icon on each row; pinned rows lift into the header (FR-16). Pinned marker color `--seal`.
- **Section headings:** `h2` serif + `label`-style count, with the section action button right-aligned.
- **Mobile (< 640px):** header stacks (photo top, name, chips); field row collapses to two lines (label over value); actions move to an overflow `⋯` menu.

### 5.4 People index (grid)

- Responsive grid: `repeat(auto-fill, minmax(240px, 1fr))`, gap 20.
- **Person card:** `--surface`, `--radius-lg`, border, `--shadow-sm` → `--shadow-md` on hover (slight `translateY(-2px)`). Contents: 56px avatar, name (`h3`), one or two pinned field values in `--text-muted`.
- Top bar: search input (grows), `[+ Add person]` primary button.

### 5.5 Documents & relationships

- **Document row:** file-type icon, title (bold), meta line `TYPE · SIZE · DATE` in `--text-muted` mono, right-aligned download/delete. Delete → confirm dialog.
- **Relationship chip:** rounded-full, `--surface`, border `--border`, avatar (20px) + name; grouped under a `label`-style relationship heading. Navigable (link). Remove = small `✕` on hover.

### 5.6 Supporting patterns

- **Confirm dialog** (delete person/field/document): centered modal, `--surface`, `--radius-lg`, `--shadow-lg`, danger primary button, scrim `rgba(28,25,23,.45)`.
- **Toast:** bottom-center, `--surface`, border, auto-dismiss 4s; success `--success`, error `--danger`.
- **Empty states:** centered icon (`--text-subtle`), one line of muted copy, one primary action.
- **Focus:** every interactive element shows the focus ring (SEC / NFR-9). Skip-to-content link on each page.

---

## 6. Iconography & imagery

- **Icons:** [Lucide](https://lucide.dev) — thin, consistent, self-hosted. 20px default, 1.75px stroke. Never the only signifier for state (pair with text/color).
- **Avatar placeholder:** initials (first + last) centered on `--accent-fill`, text `--accent`. No gravatar / external fetch (NFR-2).
- **File thumbnails:** generated server-side for images is out of scope for MVP; use type icons.

---

## 7. Implementation notes (Tailwind + CSS variables)

- Define semantic tokens as CSS custom properties on `:root` (light) and `.dark` (dark). Toggle by adding `.dark` to `<html>`; respect `prefers-color-scheme` on first load, persist choice in `localStorage`.
- Map tokens into Tailwind via `theme.extend.colors` referencing the CSS vars (e.g. `bg: 'var(--bg)'`), so utilities like `bg-surface text-text border-border` work and auto-switch with the mode.
- Self-host fonts as `woff2` under `/static/fonts`; declare with `font-display: swap`. No Google Fonts CDN.
- Ship a single tokens file (`tokens.css`) as the source of truth; document any new token here before use.

---

## 8. Open design items

- **DS-1** Final display face: Source Serif 4 (official) vs Fraunces (warmer). Default: Source Serif 4.
- **DS-2** Pinned presentation: subtle amber left-rule vs filled `--seal-fill` chip. Default: left-rule.
- **DS-3** Logo / wordmark for the chosen product name (D5). Pending name decision.
- **DS-4** Whether `select` and `file` field types (D6) need badges/inputs added to §2.4 / §5.2.
