# Lens: Visual / UI (previewable)

Fires when the diff touches view/style code — `*.tsx/jsx`, `*.vue`, `*.svelte`, Astro,
Blade/ERB/Jinja templates, SwiftUI `*.swift` views, Jetpack Compose `*.kt`, Flutter
widgets, CSS/SCSS, StyleSheet objects, Tailwind class strings, styled-components,
design-token files — or the PR body has screenshots. The reviewer's real question is
**"what does it LOOK like now, and is that intended?"** — a diff of style props does not
answer that. Get them a preview.

## Preview mechanism — 5 tiers, best → fallback

**If this lens fired, the report has a `## Visual preview` section. No exceptions.**
Silently producing nothing is the failure mode this ladder exists to prevent — a
reviewer who sees no visual section assumes there was nothing visual to see.

Try the tiers in order and use the best that succeeds. **Open the section by saying what
kind of evidence this is and why nothing better was available** — one line, so the reader
knows how much to trust it. Describe the evidence in their words; **never cite a tier
number** (see hard rule 5 — tiers are this skill's machinery, not something the reader
knows about):

> *No screenshots in the PR body and no image assets changed, so there is nothing to
> look at directly. What follows is a control-by-control inventory built from `main`.*

**Embed images as plain markdown** (`render.py` sizes them to the column) inside a
two-column table so before and after sit side by side:

```markdown
| Before | After |
|---|---|
| ![before](https://…) | ![after](https://…) |
```

1. **Author screenshots (best, nearly free).** `gh pr view <n> --json body` →
   extract every `![](…)` and `<img src="…">` URL (githubusercontent.com,
   user-attachments.githubusercontent.com). If the body has a before/after table,
   preserve that structure. Embed them. This is the ground truth the author saw.
2. **Changed image assets.** For added/modified binary images in the repo
   (`*.png/jpg/svg` under assets), render **base blob vs head blob** side by side:
   `git show <base>:<path>` vs `git show <head>:<path>`. For SVGs, embedding the two
   sources side by side is enough; for raster, link both blobs.
3. **Style-delta table (the falsifiable "preview")** — when the change is *how things
   look*. Parse the diff for changed visual props and build a before→after table. This
   fits the skill's ethos: a table the reviewer can falsify against the design.

   | Element (`file:line`) | Prop | Before | After |
   |---|---|---|---|
   | `FeedCard.tsx:42` | `fontSize` | `17` | `22` |
   | `FeedCard.tsx:43` | `fontWeight` | `600` | `700` |

   Pull: color tokens, `fontSize`/`fontWeight`/`lineHeight`, spacing
   (`margin`/`padding`/`gap`), `flex*`/layout, `borderRadius`, opacity, shadow,
   dimensions. Same table works per stack — the "Prop" column is a Tailwind utility
   (`text-lg` → `text-2xl`), a CSS custom property, a SwiftUI modifier
   (`.font(.title)`), a Compose `Modifier` chain, or a Flutter `TextStyle` field.
   **A Tailwind class-string diff is the highest-value case for this table** — the raw
   diff is one unreadable line, the table makes it falsifiable.
   **Then add a verify item: "No screenshot attached — request one, or run it."**
4. **Structural inventory** — when the change is *where things are*, not how they look.
   Screen splits, navigation/IA reorganizations, a section moved to another screen, rows
   regrouped, a component extracted into its own route. A style-delta table describes
   none of this; the reviewer's question is **"which controls moved where, and did any
   disappear?"** Build the table that answers it — one row per user-visible control, from
   the base tree, not from the new one:

   | Control | Was (`base:file:line`) | Now | Verdict |
   |---|---|---|---|
   | Rest timer | `SettingsScreen.tsx:198` | Settings → Workout & devices | moved |
   | Rate app | `SettingsScreen.tsx:567` | Profile → Help & support | **left Settings** |
   | Language | `SettingsScreen.tsx:412` | Settings → App preferences | moved |
   | Live Chat | `FeedbackSection.tsx:44` | Profile → Help & support | moved |

   **Enumerate from the base tree so a dropped control cannot be invisible** — walking
   the new screens only shows you what survived. Reconcile the counts and state them
   ("31 controls on `main`, 31 placed"). A *reachability* change — still present, but now
   two taps deeper or gone from where users look for it — is a finding even when nothing
   was deleted; grep for every entry point to the new destination and say how many there
   are. The old→new **screen map** (see `## Diagram`) is this change's architecture
   diagram, so it goes in `## What this changes` with the rest of them — the inventory
   table stays here.

   Prose is not a substitute here. *"An audit mapped every pre-existing control to a live
   new location, zero dropped"* is exactly the 90%-right claim the skill exists to
   prevent — the reader cannot check it. The table, they can.
5. **Preview build / visual regression.** If CI posts a preview URL or a diff report,
   link it prominently: Vercel, Netlify, Cloudflare Pages, Expo/EAS, Storybook or
   Chromatic, Percy, Playwright/`toHaveScreenshot` artifacts, Paparazzi (Android),
   iOSSnapshotTestCase. **A changed snapshot baseline is evidence too** — if the PR
   updates `__snapshots__`/`*.snap`/reference PNGs, that's the author asserting the new
   look is correct; surface which baselines changed and make one a verify item.

## Diagram

Usually **NOT a sequence diagram**. Prefer a small **component/layout tree** (flowchart)
showing which components changed, OR skip the diagram and let the style-delta table +
screenshots carry it. Only draw a flow diagram if the PR also changes interaction
(navigation, gesture, conditional render).

For a structural change (tier 4), draw the **old→new screen map**: two subgraphs, screens
as nodes, navigation as edges. A control that changes parent shows up as an edge landing
somewhere new, and one that leaves a screen entirely is a missing edge — both jump out of
a diagram in a way they never jump out of a file list. This is the architecture diagram,
so it belongs in `## What this changes`, not in `## Visual preview`.

## Standing checks (visual)

- **Dark mode / theme:** do changed colors use theme tokens, or are any hardcoded
  (`#fff`, `rgb(...)`) so they break in the other theme? `file:line`. Per stack: a
  missing `dark:` variant (Tailwind), a literal instead of a CSS custom property, a
  raw `Color.white` instead of a semantic/asset color (SwiftUI), a bypassed
  `MaterialTheme.colorScheme` (Compose), a hardcoded `Colors.white` (Flutter).
- **Accessibility:** contrast still adequate (WCAG AA = 4.5:1 for body text)? Touch
  target big enough — **≥44pt iOS, ≥48dp Android, ≥24px WCAG 2.2 for web**? Label
  preserved on changed controls (`accessibilityLabel`, `aria-label`,
  `contentDescription`, `Semantics`)? Is a colour the *only* thing signalling state?
- **Responsive / dynamic type:** hardcoded px/pt where the design should scale? Does the
  layout survive the largest Dynamic Type / browser zoom to 200% / longest i18n string?
  On web, does it hold at a narrow breakpoint — and did the change touch only one
  breakpoint's rules?
- **RTL:** any new `left`/`right` (vs `start`/`end`, or `ms-`/`me-` in Tailwind,
  `leading`/`trailing` in SwiftUI) that breaks RTL?
- **Motion:** new animation or transition — does it respect
  `prefers-reduced-motion` / Reduce Motion?
- **Regression surface:** is the changed component shared? List other screens that
  render it (blast radius) — a metric-size tweak on a shared card changes every feed.
- **Reachability (structural changes):** does every surface that moved still have an
  entry point, and how many? Count them by grepping for navigations to the new route. A
  screen with exactly one door, where it used to have two, is a finding.

## Verify these (visual)

- "Claims only the headline metric size changed — verify no sibling text
  (`file:line`) inherited the new size."
- "The style delta shows `X`→`Y` at `file:line` — is that the intended design value,
  or an off-by-token guess?"
- If no preview was attainable: "No visual evidence — do not approve on the diff
  alone; request a screenshot."
- Structural: "The inventory places all N controls, but *Rate app* now lives only under
  Help & support (`HelpSupportEntry.tsx:20` is its one entry point) — confirm you want it
  gone from Settings."
