# Lens: Visual / UI (previewable)

Fires when the diff touches view/style code (`*.tsx/jsx`, SwiftUI `*.swift` views,
`*.vue`, StyleSheet/CSS, color/spacing/font/layout props) or the PR body has
screenshots. The reviewer's real question is **"what does it LOOK like now, and is
that intended?"** — a diff of style props does not answer that. Get them a preview.

## Preview mechanism — 4 tiers, best → fallback

Try in order; use the best that succeeds. **Embed images as markdown** (`render.py`
renders them) under a `## Visual preview` H2.

1. **Author screenshots (best, nearly free).** `gh pr view <n> --json body` →
   extract every `![](…)` and `<img src="…">` URL (githubusercontent.com,
   user-attachments.githubusercontent.com). If the body has a before/after table,
   preserve that structure. Embed them. This is the ground truth the author saw.
2. **Changed image assets.** For added/modified binary images in the repo
   (`*.png/jpg/svg` under assets), render **base blob vs head blob** side by side:
   `git show <base>:<path>` vs `git show <head>:<path>`. For SVGs, embedding the two
   sources side by side is enough; for raster, link both blobs.
3. **No screenshots? → Style-delta table (the falsifiable "preview").** Parse the
   diff for changed visual props and build a before→after table. This fits the
   skill's ethos: a table the reviewer can falsify against the design.

   | Element (`file:line`) | Prop | Before | After |
   |---|---|---|---|
   | `FeedCard.tsx:42` | `fontSize` | `17` | `22` |
   | `FeedCard.tsx:43` | `fontWeight` | `600` | `700` |

   Pull: color tokens, `fontSize`/`fontWeight`/`lineHeight`, spacing
   (`margin`/`padding`/`gap`), `flex*`/layout, `borderRadius`, opacity, shadow,
   dimensions. **Then add a verify item: "No screenshot attached — request one, or
   run the sim."**
4. **Preview build.** If CI posts an Expo/EAS/Vercel/Netlify preview URL (check PR
   comments / checks), link it prominently.

## Diagram

Usually **NOT a sequence diagram**. Prefer a small **component/layout tree** (flowchart)
showing which components changed, OR skip the diagram and let the style-delta table +
screenshots carry it. Only draw a flow diagram if the PR also changes interaction
(navigation, gesture, conditional render).

## Standing checks (visual)

- **Dark mode / theme:** do changed colors use theme tokens, or are any hardcoded
  (`#fff`, `rgb(...)`) so they break in the other theme? `file:line`.
- **Accessibility:** contrast still adequate? touch target ≥44pt? `accessibilityLabel`
  preserved on changed controls?
- **Responsive / dynamic type:** hardcoded px/pt where the design scales with font
  size? does the layout survive the largest Dynamic Type / longest i18n string?
- **RTL:** any new `left`/`right` (vs `start`/`end`) that breaks RTL?
- **Regression surface:** is the changed component shared? List other screens that
  render it (blast radius) — a metric-size tweak on a shared card changes every feed.

## Verify these (visual)

- "Claims only the headline metric size changed — verify no sibling text
  (`file:line`) inherited the new size."
- "The style delta shows `X`→`Y` at `file:line` — is that the intended design value,
  or an off-by-token guess?"
- If no preview was attainable: "No visual evidence — do not approve on the diff
  alone; request a screenshot."
