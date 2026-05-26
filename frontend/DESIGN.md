# Design Language

The aesthetic is typographic, flat, and editorial. One background color. 1px rules do all the structural work. Type scale contrast carries all hierarchy — not surfaces, shadows, or decoration. The table is the page.

---

## Color

All colors are pure neutral greys — equal R/G/B values, no blue cast.

### Base

| Role           | Value     | Usage                                          |
| -------------- | --------- | ---------------------------------------------- |
| Background     | `#111111` | The one background. Used everywhere on pages.  |
| Surface raised | `#252525` | Modals, dropdowns only — not cards, not panels |
| Border         | `#303030` | 1px horizontal rules between rows and sections |
| Text primary   | `#d4d4d4` | All primary text                               |
| Text secondary | `#737373` | Labels, column headers, metadata               |
| Text disabled  | `#444444` | Disabled state text                            |
| Accent         | `#ffffff` | Links, focus indicators, active state          |
| Highlight      | `#c96060` | Text mark / selection bg                       |

There is no `surface` token for page-level use. Cards and panels with background fills do not exist. The only background on a page is `canon-bg`.

### Semantic

Reserved exclusively for status communication — never decorative.

| Role    | Value     | Usage                       |
| ------- | --------- | --------------------------- |
| Success | `#3d9e6a` | Completed, passing, healthy |
| Warning | `#c9951a` | Degraded, pending, at-risk  |
| Error   | `#c94040` | Failed, blocked, critical   |
| Info    | `#8888aa` | Informational, in-progress  |

Semantic badge pairs (muted bg for inline status):

| Role    | Background | Text      |
| ------- | ---------- | --------- |
| Success | `#1a3d2a`  | `#4ade80` |
| Warning | `#3d2e0a`  | `#f0b429` |
| Error   | `#3d1a1a`  | `#f87171` |
| Info    | `#1a2a3d`  | `#93c5fd` |

### Interactive State Overlays

Applied on top of any surface:

| State               | Overlay                     |
| ------------------- | --------------------------- |
| Hover               | `rgba(255,255,255, 0.05)`   |
| Active / Pressed    | `rgba(0,0,0, 0.12)`         |
| Focus               | 2px solid `#ffffff` outline |
| Disabled            | Element opacity `0.38`      |
| Selected (row, tab) | `rgba(255,255,255, 0.08)`   |

---

## Typography

Three typefaces. Base font size: `17px` on `<html>`.

| Role      | Family         | Source                                                                     | Weights |
| --------- | -------------- | -------------------------------------------------------------------------- | ------- |
| Condensed | ROM Condensed  | `https://type.cargo.site/files/CargoROMCondensedVariable.woff2` (variable) | 100–900 |
| Regular   | ROM            | `https://type.cargo.site/files/CargoROMVariable.woff2` (variable)          | 100–900 |
| Mono      | Gaisyr Mono    | `https://type.cargo.site/files/CargoGaisyrMono-Book.woff2`                 | 400     |

### Scale

| Role           | Typeface  | Size      | Weight | Style             |
| -------------- | --------- | --------- | ------ | ----------------- |
| Display        | Condensed | 2.5rem    | 700    | Upright           |
| Heading        | Condensed | 1.25rem   | 700    | Upright           |
| Label          | Condensed | 0.75rem   | 700    | Uppercase, 0.08em |
| Body           | Regular   | 0.875rem  | 400    | Upright           |
| Body small     | Regular   | 0.75rem   | 400    | Upright           |
| Code / Mono    | Monospace | 0.8125rem | 400    | Upright           |
| Error / Helper | Regular   | 0.75rem   | 400    | Upright           |

**Display** is used for the primary identifier in every table row — session titles, entity names, primary data. It is large (2.5rem) and bold. This is the defining visual element of the aesthetic.

**Label** is tiny. Column headers, nav links, metadata, timestamps, badges, section markers, button text — all label scale. The contrast between label (tiny) and display (huge) is the aesthetic.

**Body** is for prose: descriptions, detail text, form field content.

---

## Spacing

Base unit: `4px`. All spacing is a multiple of this unit.

| Token      | Value | Usage                                 |
| ---------- | ----- | ------------------------------------- |
| `space-1`  | 4px   | Icon padding, tight inline gaps       |
| `space-2`  | 8px   | Badge padding, tight row padding      |
| `space-3`  | 12px  | Row vertical padding                  |
| `space-4`  | 16px  | Default component padding             |
| `space-6`  | 24px  | Section gap                           |
| `space-8`  | 32px  | Large section gap                     |
| `space-12` | 48px  | Between major sections in detail view |
| `space-16` | 64px  | Page-level vertical rhythm            |

Horizontal page margin: `20px`. Applied to page content, not header elements.

---

## Layout

### Shell

```
┌──────────────────────────────────────────────────────┐
│ Header (single row) — brand · nav links · logout     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Full-width content area (20px horizontal margin)   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- **No sidebar.** Navigation lives in the header only.
- **No max-width constraint** on the content area. Content fills the viewport width minus 20px margins.
- **Header background is `canon-bg`** — identical to the page. It is distinguished only by a 1px bottom border.
- Main content area scrolls; header does not.

### Header

Single row. 1px bottom border. Full-width.

```
[CANON]                                    [nav links]   [logout]
```

- All header text: label scale, condensed bold, uppercase.
- Nav links: label scale, separated by spacing (no decorators). Active: `text-primary`. Inactive: `text-secondary`, hover to `text-primary`. No underlines, no background on active.
- No username shown in the header.

### Auth Pages

Centered on the full viewport. No card, no border, no background surface.

```
[brand wordmark — label scale, text-secondary]
[Page title — display scale, 2.5rem]
[form fields — underline inputs]
[submit — plain text, label scale]
[secondary link]
```

### Content Views

**Table view** — the primary view for list pages (dashboard, etc.):

The table is full-bleed within the 20px page margin. No card borders. No background fills. Rows separated by 1px bottom border only.

```
[Column headers — label scale, text-secondary]
─────────────────────────────────────────────── 1px rule
[Primary column — display scale, 2.5rem]   [Secondary cols — label scale]
─────────────────────────────────────────────── 1px rule
[Primary column — display scale, 2.5rem]   [Secondary cols — label scale]
─────────────────────────────────────────────── 1px rule
```

**Detail / Form view** — for record pages, settings, forms:

Two columns. 1px horizontal rules separate rows. No card backgrounds. Borders span the full page width.

```
[Label — label scale, text-secondary, ~33%]   [Content — body scale, ~67%]
──────────────────────────────────────────────────────────────── 1px rule (full-bleed)
[Label — label scale, text-secondary, ~33%]   [Content — body scale, ~67%]
```

---

## Components

### Buttons

Buttons are plain text — not boxed. Label scale, condensed bold, uppercase, `0.08em` letter-spacing. No border-radius. No background fill on default state.

| Variant     | Text color       | Hover            |
| ----------- | ---------------- | ---------------- |
| Primary     | `text-primary`   | `text-secondary` |
| Ghost       | `text-secondary` | `text-primary`   |
| Destructive | `canon-error`    | dimmed           |

- Disabled: opacity `0.38`.
- No boxed/outlined button variant. No filled background buttons for inline actions.

### Form Inputs

**Typographic style (default for all forms):**

- Bottom border only — no full border box.
- Background: transparent (sits on page background).
- Default: 1px bottom `canon-border`.
- Focus: 1px bottom `canon-accent` (`#ffffff`).
- Text: body scale, `text-primary`. Placeholder: `text-secondary`.
- No border-radius.

**Field anatomy:**

```
[Label — label scale, uppercase, text-secondary]
[Input — underline only]
[Helper text or Error — body small, text-secondary / error]
```

Label always above input, never floating. Error replaces helper; never shown simultaneously.

### Status Badges

Inline status indicator, never decorative.

- Label scale, uppercase.
- No border-radius.
- Use semantic background/text pairs.

Examples: `PASSING`, `FAILED`, `PENDING`, `RUNNING`

### Data Tables

The primary layout pattern. Full-bleed. No card wrapper.

**Column headers:**

- Label scale, uppercase, `text-secondary`.
- 1px bottom border below the header row.

**Rows:**

- Primary column: display scale (2.5rem), condensed bold, `text-primary`.
- All other columns: label scale, `text-secondary`.
- Row padding: `12px` vertical, `0` horizontal (page margin handles it).
- 1px bottom border per row.
- Hover: white overlay on full row.
- Entire row is a link target where applicable.

**Empty state:**

- Full-width, centered. Body scale heading + body small description. No illustrations.

### Navigation

**Header nav links:**

- Label scale, uppercase.
- Active: `text-primary`. No underline, no background.
- Inactive: `text-secondary`, hover to `text-primary`.

**Breadcrumbs:**

- Label scale.
- Separator: `·` in `text-secondary`.
- Current: `text-primary`. Ancestors: `text-secondary`.

### Modals

- Background: `canon-surface-raised` (`#252525`).
- 1px border: `canon-border`.
- No border-radius.
- Max-width: `560px` (form), `800px` (detail/preview).
- Backdrop: `rgba(0,0,0, 0.5)`.
- Header: heading scale + close button (ghost), 1px bottom border.
- Footer: right-aligned buttons, 1px top border.
- `Escape` to close, backdrop click to close.

### Toasts

- Fixed, bottom-right, `16px` from edges.
- Width: `320px`.
- Background: `#252525`. 1px border `canon-border`.
- Left 4px border in semantic color.
- Body scale. Auto-dismiss 5s. Manual close `×`.
- Stack vertically, newest on top.

---

## Principles

1. **The table is the page.** The primary content is a full-bleed table. There are no cards, panels, or sidebars on the primary content surface. The background is one color throughout.
2. **Type scale is the only hierarchy.** Display (2.5rem) vs label (0.75rem) — a 4x ratio. This contrast is the entire visual language. Nothing else does organizational work.
3. **Labels are tiny. Data is huge.** Column headers, metadata, timestamps, nav links — all label scale. Session titles, entity names, primary identifiers — all display scale. Never invert this.
4. **Navigation is peripheral.** Nav links live in the header at label scale. They do not compete with content.
5. **One background.** Pages render directly on `canon-bg`. `canon-surface-raised` is for modals only.
6. **Accent sparingly, semantic never decoratively.** White (`#ffffff`) for focus and active indicators. Semantic colors (error, warning, success, info) for status only — never for decoration or branding.
7. **No border-radius.** Sharp corners throughout — inputs, buttons, modals, badges.
8. **No ornamentation.** No icons as decoration, no gradients, no shadows (except modal backdrop). Text over everything.
9. **Pure neutrals.** All greys have equal R/G/B — no blue or warm cast anywhere in the palette.
