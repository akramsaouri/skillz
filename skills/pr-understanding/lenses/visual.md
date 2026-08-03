# Lens: Visual / UI (previewable)

Fires when the diff touches view/style code — `*.tsx/jsx`, `*.vue`, `*.svelte`, Astro,
Blade/ERB/Jinja templates, SwiftUI `*.swift` views, Jetpack Compose `*.kt`, Flutter
widgets, CSS/SCSS, StyleSheet objects, Tailwind class strings, styled-components,
design-token files — or the PR body has screenshots. The reviewer's real question is
**"what does it LOOK like now, and is that intended?"** — a diff of style props does not
answer that. Get them a preview.

## The section SHOWS. It does not explain.

This is the one section of the report whose job is pictures. Everything the reader needs
to *see* goes here; everything they need to *know* goes in another section. Concretely,
`## Visual preview` is exactly three things:

1. **One line** naming what kind of evidence this is, and why nothing better was
   available — so the reader knows how much to trust it.
2. **The artifact.** Pixels if they exist; a reconstruction if they don't.
3. *(optional)* a `<details>` holding the numeric backup — the style delta, the control
   inventory.

Nothing else. In particular:

- A paragraph opening *"Two things a designer should look at…"* is a **finding**. It goes
  under `## Findings`.
- A sentence about hardcoded colors or a token mismatch is a **standing check**. It goes
  in that row, at a `file:line`.
- A paragraph narrating the restructure — *"the old `actionBar` was the footer; it has
  been split, a new `fixedFooter` inherits the padding and becomes the flex parent"* — is
  precisely what the picture is FOR. If you are writing that sentence, you have not drawn
  the thing yet. Draw it and delete the sentence.

The test: **delete every word of prose from the section. Does what remains still answer
"what does this look like now?"** If the section collapses into an essay, it failed —
however accurate the essay is. A wall of text here is the same defect as a wall of text
anywhere in this skill, and it is the *easiest* one to fall into, because describing a
layout is much less work than reconstructing it.

**Describe the evidence in the reader's words; never cite a tier number** (see hard rule
5 — the ladder below is this skill's machinery, not something the reader knows about):

> *No screenshots in the PR body and no preview build, so the panels below are rebuilt
> from the diff — not captures.*

## Preview ladder — best → fallback

**What is mandatory is the work, not the section.** If view code changed you must decide
whether the *user-visible result* changed — and if it did, show it. Silently skipping
that decision is the failure mode this ladder exists to prevent.

Try the tiers in order and use the best that succeeds. The lower tiers build their
artifact out of the diff itself, so "no screenshots" is almost never "nothing to show".
If you reach the bottom with genuinely nothing, the lens misfired — a view file changed,
but only its data path, no visual property and no structure. **Do not emit an empty
section saying so:** a `## Visual preview` that reads "no visual evidence available"
implies a visual change went unexamined. Drop the section and put the finding in one
`## Standing checks` row instead, where it is still falsifiable and costs a line rather
than a heading:

| Any user-visible change? | **No** | the `*.tsx` edits are all in the data path — `useFeed.ts:40-58`; no style prop, layout or route touched |

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
3. **Preview build / visual regression.** Real pixels somebody else already rendered. If
   CI posts a preview URL or a diff report, lead with it: Vercel, Netlify, Cloudflare
   Pages, Expo/EAS, Storybook or Chromatic, Percy, Playwright/`toHaveScreenshot`
   artifacts, Paparazzi (Android), iOSSnapshotTestCase. **A changed snapshot baseline is
   evidence too** — if the PR updates `__snapshots__`/`*.snap`/reference PNGs, that's the
   author asserting the new look is correct; surface which baselines changed and make one
   a verify item.
4. **Reconstructed mock — draw it yourself.** No screenshots and no preview build, but
   the diff still *specifies a layout*: a view tree (JSX, SwiftUI, Compose, a template)
   plus the style values it references. That is enough to rebuild the component at
   wireframe fidelity and stand before next to after. This is as close to pixels as you
   get without running the app, and it is what the reviewer actually wanted.

   `render.py` passes raw HTML straight through, and the page's own CSS variables keep
   the mock working in both light and dark:

   ```html
   <div class="pv">
   <figure><figcaption>Before</figcaption>
   <div class="mock">
   <div class="row"><span class="btn">Discard</span><span class="btn">Publish</span></div>
   </div>
   </figure>
   <figure><figcaption>After</figcaption>
   <div class="mock">
   <div class="row is-new" style="gap:12px;background:var(--code-bg);border:1px solid var(--border);border-radius:10px;padding:12px">
   <span style="width:36px;height:36px;border-radius:50%;background:var(--accent-weak);flex:none"></span>
   <span>2 changes vs your routine</span>
   </div>
   <div class="row"><span class="btn">Discard</span><span class="btn">Publish</span></div>
   </div>
   </figure>
   </div>
   ```

   Classes the renderer provides: `.pv` (the side-by-side grid — one `<figure>` per
   panel), `.mock` (the frame), `.row`, `.btn`, `.ph` (a grey placeholder bar),
   `.is-new` (green outline: this PR adds it), `.is-gone` (red dashed: this PR removes
   it). Everything else is an inline `style=""` carrying the diff's real numbers.
   **No blank lines inside the markup** — a blank line ends the HTML block and the rest
   gets parsed as markdown.

   Rules that keep a *drawing* falsifiable:

   - **Label it a reconstruction, once, above the figure.** "Rebuilt from the diff, not a
     screenshot." The reader must never mistake it for a capture.
   - **Draw only what the code states.** Order, nesting, spacing, radius, colour and
     dimensions come from the view tree and the style object. If you are inventing more
     than the arrangement, stop and fall back to the table.
   - **Real strings.** Copy literals or resolved i18n values out of the code. Never
     invent labels, never paraphrase, never "Lorem".
   - **Wireframe fidelity, not pixel fidelity.** Grey `.ph` bars for content the change
     doesn't touch; real values only where the change *is* the value. A mock straining to
     look like a screenshot invites trust in details you never verified.
   - **Mark the delta.** `.is-new` / `.is-gone` on what the PR adds and removes. Without
     them the reader is diffing two pictures by eye — the job you were supposed to do.
   - **Anchor it.** One line under the figure citing the `file:line` the structure and the
     values came from.
5. **Fallback tables.** Nothing to capture and nothing coherent to draw — a value sweep
   across forty files, or an IA change where the picture is the screen map. Pick the table
   by change shape. **When you did draw a mock, the matching table still belongs here, but
   inside `<details>` as the numeric backup — the picture leads.**

   **Style delta** — when the change is *how things look*:

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

   **Structural inventory** — when the change is *where things are*, not how they look.
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

## Diagram

Usually **NOT a sequence diagram**. Prefer a small **component/layout tree** (flowchart)
showing which components changed, OR skip the diagram and let the preview carry it — a
mock or a screenshot already shows the layout, and a flowchart of the same boxes is
duplicate work. Only draw a flow diagram if the PR also changes interaction (navigation,
gesture, conditional render).

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
- Whenever the preview is a mock: "The panels are drawn from `file:line`, not captured —
  the CTA is a 36pt disc above the button row. Run the screen once and confirm the real
  thing matches before approving."
- If no preview was attainable: "No visual evidence — do not approve on the diff
  alone; request a screenshot."
- Structural: "The inventory places all N controls, but *Rate app* now lives only under
  Help & support (`HelpSupportEntry.tsx:20` is its one entry point) — confirm you want it
  gone from Settings."
