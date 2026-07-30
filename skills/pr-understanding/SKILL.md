---
name: pr-understanding
description: >
  Understand a pull request, diff, or branch by building a falsifiable MAP
  instead of a prose summary. Use when the user wants to grasp what a change
  does before merging it, especially AI-written code.
---

# PR Understanding

**Premise.** With AI writing the code, the diff is cheap and *understanding* it is
the expensive part. A prose summary that is 90% right is more dangerous than a diff
you struggled through — the wrong 10% is invisible. Your job is NOT to summarize.
Your job is to produce a **map the user can falsify at a glance**: a wrong arrow in
a diagram jumps out in a way a wrong sentence never does.

**Altitude — lead with the shape, land on the load-bearing detail.** Work
*architecture-first*: what moved, which boundaries it crosses (client↔edge↔DB↔
storage, module↔module, screen↔navigator), what the new control/data flow is, and
where the risk concentrates. Drill into a specific `file:line` **only when it
carries weight** — a security re-check, an invariant, a behavioral edge, a
one-character change that flips behavior. A citation is the *evidence* for a
load-bearing claim, not a line-by-line tour. Every bullet either establishes the
*shape* or flags something the reader must *verify* — if a detail changes neither,
cut it or fold it into a collapsed `<details>` block.

## Hard rules

1. **Never emit a prose summary of what the PR does.** No "This PR refactors…"
   paragraph anywhere in the output. The output is the sections below and nothing
   else.
2. **Every claim is falsifiable and located.** Cite `file:line`. If you cannot
   point to it, do not assert it.

## Step 1 — Acquire the change (net diff + a tree to read)

You always need **two** things: the *net* diff, and a checked-out tree at the right
commit (later subagents grep the repo, not just the patch).

**Open PR, by number:**
- Net diff: `gh pr diff <n>`. **Do NOT add `--patch`** — that returns the per-commit
  mbox *series*, so a file touched by two commits appears twice and a rename shows as
  add-then-rename. Pure noise.
- Metadata: `gh pr view <n> --json title,body,files,state,mergedAt,headRefName,mergeCommit,additions,deletions`.
- Tree: `gh pr checkout <n>` (uses the gh token; a plain `git fetch https://…` can fail
  when the remote is SSH-only).

**Merged / closed PR** — the head branch is usually **deleted**, so
`git fetch origin <head>` fails. Use the merge commit instead:
- `SHA=$(gh pr view <n> --json mergeCommit -q .mergeCommit.oid)`
- Net diff of just this PR: `git diff "$SHA^" "$SHA"`.
- **The tree you cloned is at `main`, NOT at the PR.** `main` has moved on; reading it
  and citing the PR is the #1 source of confidently-wrong line numbers. Materialize the
  PR's tree before you grep or cite:
  `git worktree add /tmp/pr-<n>-tree "$SHA"` — then read and cite paths under that
  worktree. (`git show "$SHA":<path>` works for one-off reads.)
- Every `file:line` in the report MUST resolve against `$SHA`, not `main`. If you also
  looked at `main` — e.g. to check whether a bug still exists — label that claim
  explicitly as "at main today", never silently.

**Branch / ref range:** `git diff <base>...<head>`. **Working tree:** `git diff`.

**No local clone?** `gh repo clone <owner>/<repo> /tmp/<repo> -- --depth 50` (token auth).

Capture the net patch, the changed-file list with +/- counts, and the title/description if
one exists. You will **fact-check the description against the code** — never trust it.

## Step 2 — Triage: fingerprint → route (lane × lens)

This is the step that stops the skill from being generic. Fingerprint the PR from the
`--stat`, the file paths, and content signals, then set two independent dials.

### First, compute MEANINGFUL churn

Size is measured on **meaningful** churn, not raw `+/-`. **Exclude** from the count:
lockfiles (`*.lock`, `package-lock.json`, `Podfile.lock`, `yarn.lock`, `Cargo.lock`,
`Package.resolved`), snapshots (`__snapshots__`, `*.snap`), generated code (`*.g.dart`,
`*.pb.go`, `openapi`/`graphql` codegen, `dist/`, `build/`), vendored deps, and pure
moves/renames. A `pod install` lockfile bump must not fake "large". Note the excluded
files — the *Reading order* section will list them under "Ignore".

### Axis 1 — SIZE → lane (how much machinery)

| Lane | Trigger (on meaningful churn) | What changes vs Standard |
|---|---|---|
| **Fast** | ≤~3 meaningful files, single concern, low blast radius (no exported-signature / schema / auth / money change) | **Skip the parallel fan-out** (do a quick inline caller/test check instead). ≤1 diagram (skip if the flow is unchanged). 2–3 verify items. Still renders. |
| **Standard** | a normal PR | The full Steps 3–7 below, inline (fan out only if blast radius looks non-trivial). |
| **Deep** | ≥~10 meaningful files, OR crosses a boundary (client↔edge↔DB, new native module), OR high blast radius, OR touches migrations / auth / money | **Full parallel fan-out** (Step 3), old-vs-new diagrams, extra scrutiny, more verify items. |

When unsure between two lanes, pick the **larger** — under-reading a big PR is the
expensive mistake.

### Axis 2 — SCOPE → lens (which questions, diagram, checks, sections)

Match the PR against the lenses below. **A PR may get one primary lens + secondary
lenses** (a feature that adds a migration is Feature × Migration). For each matched
lens, **read its file** and fold its guidance into the relevant steps:

| Lens | Fires when… | Lens file |
|---|---|---|
| **Visual / UI** *(previewable)* | changes touch view files (`*.tsx/jsx`, SwiftUI/`*.swift` views, `*.vue`), StyleSheet/CSS, color/spacing/font/layout props; or the PR body has screenshots | `lenses/visual.md` |
| **Migration / schema** | `*.sql`, `**/migrations/**`, `supabase/migrations`, Prisma/Drizzle schema, any DB DDL | `lenses/migration.md` |
| **Dependency bump** | only manifests + lockfiles change (`package.json`, `Podfile`, `go.mod`, `Cargo.toml`, `*.gradle`) — version numbers, no app logic | `lenses/dependency.md` |
| **Refactor / no-behavior-change** | renames, moves, de-exports, extractions, type-only edits; author *claims* no behavior change | `lenses/refactor.md` |
| **Feature / new flow** | new screens/routes/endpoints/files introducing behavior | `lenses/feature.md` |
| **Bugfix** | title/body says fix; small targeted change to existing logic | `lenses/bugfix.md` |
| **Config / CI / infra** | `.github/`, CI yaml, Dockerfiles, env/secrets, build config | `lenses/config.md` |

If **nothing** matches cleanly, treat it as **Feature/Standard** and note the
ambiguity as the first *verify* item.

**State the routing decision at the top of the report**, one line, so the user can
falsify the triage itself:
> **Triage:** Deep lane · Feature × Migration lens · 14 meaningful files (3 lockfile/snapshot files ignored).

## Step 3 — Blast radius (lane-gated)

**Deep lane → fan out PARALLEL subagents.** One `Task` each, dispatched together in a
single message so they run concurrently. Each returns a compact `file:line` bullet
list, no prose:

- **Callers** — for every exported/changed function, symbol, endpoint or RPC, who
  calls it, and are the call sites compatible with the new signature/behavior?
- **Tests** — which existing tests exercise the changed paths; are any now stale,
  missing, or newly required?
- **Type & schema usage** — every use site of changed types/interfaces/DB
  columns/API shapes; flag any the diff did NOT update.
- **Config / env / migration touch points** — new env vars, flags, migrations, or
  generated code this change implies.

**Standard lane →** fan out only if blast radius looks non-trivial; otherwise a quick
inline grep for callers + tests of the changed symbols is enough.

**Fast lane →** skip the fan-out; one inline check that the changed symbol's callers
and tests are compatible.

Merge into one **Blast Radius** section. Anything found that the diff did NOT touch is a
candidate risk — highlight it. (Lenses add their own blast-radius targets, e.g. the
Dependency lens greps the changelog for breaking changes, not the repo.)

## Step 4 — Reading order

Where to start, what to ignore:
- **Load-bearing** — the 1–3 files where the actual behavior change lives. Start here.
- **Supporting** — files that follow from the load-bearing change.
- **Ignore** — generated, moved, renamed, or pure-format churn (the excluded set from
  Step 2's meaningful-churn count). Say *why* it is safe to skip.

**Every changed file from Step 1 lands in exactly one bucket.** Count them against the
changed-file list — if the totals disagree, you dropped a file.

## Step 5 — Diagram the CHANGED flow (Mermaid)

**Lead with architecture.** The first diagram shows the change at the level of
*components and boundaries* — the modules/services/layers touched and how data crosses
between them. Only THEN, if a specific mechanism carries the risk, add a second, tighter
diagram. **The matched lens's `## Diagram` section picks the type — follow it.** Skip
the diagram entirely on the Fast lane when the flow is unchanged.

Pick the detail type from the change shape:
- Request / RPC / API / event path → **sequenceDiagram**.
- Branching logic, lifecycle, status machine → **flowchart** / **stateDiagram-v2**.
- Data-model / relationship change → **erDiagram** or a small **classDiagram**.

When behavior changes, show **old path vs new path**. Depict *this change*, not the
whole system.

**Mermaid hygiene — a diagram that fails to parse is worse than no diagram.** The
renderer degrades a broken diagram to a source block, but a rendered diagram is the
point — keep the source parseable:
- **flowchart / stateDiagram / class / ER — quote every node and edge label:**
  `A["text"]`, `D{"choice?"}`, `X -->|"label"| Y`. Quoting neutralizes `(){}[]`, `:`,
  `<`/`>`, `#`, `"`, and a leading `-`. When in doubt, quote.
- **sequenceDiagram messages — do NOT quote** (quotes render literally). The one real
  hazard is **`;`** — it silently truncates the message. Use a **comma** instead.
- Keep `file:line` citations OUT of diagram labels. Cite in surrounding prose.

## Step 6 — Standing checks (repo-aware invariants)

Run the checks that are load-bearing for THIS diff. **This is the highest-leverage
part of the skill.** Answer each with a `file:line`.

**Never mention the skill's own configuration state in the report.** The reader wants
a map of their PR, not a note about which section was tuned.

Ceiling: **6 rows** (Deep: 8). A check that is "N/A" for this PR is not a row — drop
it. Prefer one check you can falsify at a `file:line` over three you answer "N-A".

Derive the check-set in this order:
1. The repo's own stated rules — CLAUDE.md / AGENTS.md / CONTRIBUTING, a lint or CI
   config. Cite where you got it.
2. The matched lens's `## Standing checks (…)` section.
3. The defaults below, only where the stack makes them apply.

Defaults, applied only when relevant:
- Auth/tenancy: do new DB reads/writes preserve row-level security and user scoping?
- Money: are amounts still in minor units — no float, no major-unit leak?
- Time: stored UTC, formatted local only at the edge?
- External calls: any new call without a timeout or error path?
- Secrets: any token, key or PII newly logged?
- React/RN: any hook called conditionally or in a loop / `.map()`? Does the hook COUNT
  stay stable across renders?
- Swift/Kotlin: any main-thread blocking, retained self, or lifecycle-unsafe capture?

## Step 7 — "Verify these"

Restate the PR's implicit claims as **falsifiable questions the user checks against
the code** — count scales with the lane (Fast 2–3, Deep 5–7+), and **the lens's
`## Verify these (…)` section supplies its own**. Shape:
> "Claims the retry only fires on 5xx — verify at `api/client.ts:88` that a 4xx
> falls through without retrying."

Do not skip **trivial-looking edits that change behavior**: `||`→`??`, `===`→`==`, an
added `await`, a flipped default, a removed `!`. A one-character diff can be the whole PR.

## Step 8 — Render (and re-render on every revision)

Assemble Steps 2–7 as one markdown document — **open with the Triage line**, then H2 per
section, fenced ```mermaid for diagrams, deep-but-skippable content in
`<details><summary>…</summary>`. Then render and open it:

```bash
printf '%s' "$REPORT" | python3 "<this-skill-dir>/render.py" --title "PR #<n>"
# or: python3 "<this-skill-dir>/render.py" --title "PR #<n>" report.md
```

The title determines a **stable output path**, so **re-running updates the same artifact
in place**. Keep the title identical across re-renders of the same PR. The page is
ephemeral and lives in a temp dir — **commit nothing**.

**Rendering is the last action of every run.** If you change anything after the first
render, regenerate so the page is never stale, then report the path and **stop** — the
page is the deliverable, not a chat recap.
