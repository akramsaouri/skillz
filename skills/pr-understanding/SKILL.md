---
name: pr-understanding
description: >
  Understand a pull request, diff, or branch by building a falsifiable MAP
  instead of a prose summary. Use when the user wants to grasp what a change
  does before merging it, especially AI-written code.
---

# PR Understanding

**Premise.** With AI writing the code, the diff is cheap and *understanding* it is
the expensive part. A summary that is 90% right is more dangerous than a diff you
struggled through — the wrong 10% is invisible. So produce a **map the user can falsify
at a glance**: a wrong arrow in a diagram jumps out in a way a wrong sentence never does.
Say plainly what the change is — then make every part of that claim checkable.

**Altitude — lead with the shape, land on the load-bearing detail.** Work
*architecture-first*: what moved, which boundaries it crosses (client↔edge↔DB↔
storage, module↔module, screen↔navigator), what the new control/data flow is, and
where the change's weight lands. Drill into a specific `file:line` **only when it
carries weight** — a security re-check, an invariant, a behavioral edge, a
one-character change that flips behavior. A citation is the *evidence* for a
load-bearing claim, not a line-by-line tour. Every bullet either establishes the
*shape* or flags something the reader must *verify* — if a detail changes neither,
cut it or fold it into a collapsed `<details>` block.

## Hard rules

1. **Explain the change; never critique it.** This skill draws a map, not a verdict.
   What the change does, what moved, which boundaries it crosses, what follows from it,
   what history explains the present state, what it touches outside the diff — all in.
   Whether it is *wrong, risky, missing something, or badly done* — out, along with any
   hunt for a bug class the diff didn't raise. The litmus test: **would this observation
   still be worth writing if the PR were perfect?** If yes it is explanation and belongs
   here; if it exists only because something might be wrong, it is critique and does not.
   Defect-hunting is a **separate rail's** job — `/code-review` fields finder and
   verifier agents, confidence verdicts, quoted counter-evidence and cross-finder dedup,
   none of which this skill has. Doing it badly here costs the budget that should go to
   making the change legible.
2. **Every claim is falsifiable and located.** Cite `file:line`. If you cannot
   point to it, do not assert it.
3. **Explain the change plainly, but never vaguely.** "This PR refactors the auth layer
   to improve maintainability" is banned — it is unfalsifiable and says nothing. "The
   1200-line `SettingsScreen` becomes a 4-category hub plus 4 sub-screens
   (`Navigation.tsx:384-389`)" is required. The test is not *"is this prose?"* but
   *"can the reader prove me wrong from the code?"*
4. **Quote the PR body before comparing it to the code.** Never write "the PR body
   claims X" without the author's actual words at first mention. The reader must be able
   to compare claim against reality without leaving the page.
5. **Never hand-write an identity line.** Author, state, link, dates, churn and branches
   are rendered from `--meta` (Step 8). A `PR #631 — branch → main · +2789/−1784` line in
   the markdown double-renders.
6. **Never mention the skill's own machinery in the report body.** No lanes, no tier
   numbers, no step numbers, no notes about which section was tuned — the reader wants a
   map of their PR, not a description of how it was made.
   The line is **provenance, not vocabulary**: calling the change a bugfix or a migration
   is plain English and fine; tagging a row `(bugfix)` to mark which lens supplied the
   check is machinery and is not. If a phrase would puzzle someone who has never heard of
   this skill, cut it.
   The one exception is the header: `--triage` (Step 8) prints the lane and lens as chips,
   deliberately, so the routing stays falsifiable. That is chrome, not the markdown.

## Step 1 — Acquire the change (net diff + commit list + a tree to read)

You need **three** things: the *net* diff, the *commit list*, and a tree at the PR's
own commit (later subagents grep the repo, not just the patch).

**PR by number — this works whether it is open, merged or closed:**

```bash
SHA=$(gh pr view <n> --json headRefOid -q .headRefOid)   # pin it ONCE — see the FETCH_HEAD trap
gh pr diff <n>                                     # net diff — see the --patch warning below
gh pr view <n> --json title,body,author,url,number,state,isDraft,createdAt,mergedAt,closedAt,headRefName,baseRefName,mergeCommit,additions,deletions,changedFiles,files > /tmp/pr-<n>-meta.json
git fetch origin refs/pull/<n>/head                # brings $SHA's objects local — works even if the branch was deleted
git worktree add /tmp/pr-<n>-tree "$SHA"           # read and cite against THIS path
gh pr view <n> --json commits \
  -q '.commits[] | "\(.oid[0:8])  \(.messageHeadline)"'   # the commit list — see below
git show --stat --oneline <oid>                    # what any one commit touched
```

**The `FETCH_HEAD` trap — this one fails silently.** `FETCH_HEAD` is a scratch file, not
a ref: the *next* `git fetch` of any kind overwrites it, including one run by a subagent
or by you refreshing the base branch. So `git diff origin/<base>...FETCH_HEAD -- some/file`
can return **0 bytes and exit 0** long after you thought you had pinned the PR — reading
as "this file is unchanged" when it is not. Resolve `$SHA` once, up front, and use it
everywhere. Never read `FETCH_HEAD` twice.

- **Do NOT use `gh pr diff --patch`** — that returns the per-commit mbox *series*, so a
  file touched by two commits appears twice and a rename shows as add-then-rename. Pure
  noise. Get per-commit history from the commit list instead.
- **Do NOT `gh pr checkout`.** It moves the user's working tree onto the PR branch. The
  worktree above leaves their repo where they left it.
- **The clone is at `main`, NOT at the PR.** Reading `main` and citing the PR is the #1
  source of confidently-wrong line numbers. Every `file:line` in the report MUST resolve
  against `/tmp/pr-<n>-tree`. If you also looked at `main` — e.g. to check whether a bug
  still exists — label that claim explicitly as "at main today", never silently.
- `git show "$SHA":<path>` works for one-off reads; `origin/<base>:<path>` for the
  before-state.
- **Take the commit list from `gh`, not from a `git log` range.** `origin/<base>..FETCH_HEAD`
  is empty for a merge-committed PR (its commits are already ancestors of the base) and
  silently wrong whenever the local `origin/<base>` is stale. `gh pr view --json commits`
  is authoritative in every state.

**Read the commit list, not just the net diff.** The net diff is what merges; the commit
list is what *happened*, and the two disagree in ways that are always worth a look:
- **Added then deleted nets to zero.** A test introduced in one commit and removed in the
  next is invisible in `gh pr diff` — and is often the most important thing in the PR.
- A commit message that contradicts the body, or reverses an earlier commit.
- A "fix review feedback" commit that quietly widens scope.

If a later commit undoes an earlier one, say so and quote the message: the author decided
something mid-PR, and the reasoning is rarely written down anywhere else.

**Branch / ref range:** `git diff <base>...<head>` plus `git log --oneline <base>..<head>`.
**Working tree:** `git diff`.

**No local clone?** `gh repo clone <owner>/<repo> /tmp/<repo> -- --depth 50` (token auth).

Capture the net patch, the changed-file list with +/- counts, and the title/description if
one exists. You will **fact-check the description against the code** — never trust it.

## Step 2 — Triage: fingerprint → route (lane × lens)

This is the step that stops the skill from being generic. Fingerprint the PR from the
`--stat`, the file paths, and content signals, then set two independent dials.

### First, compute MEANINGFUL churn

Size is measured on **meaningful** churn, not raw `+/-`. **Exclude** from the count:
- **Lockfiles** — `*.lock`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`,
  `Podfile.lock`, `Package.resolved`, `Cargo.lock`, `go.sum`, `poetry.lock`, `uv.lock`,
  `Gemfile.lock`, `composer.lock`, `pubspec.lock`, `mix.lock`.
- **Snapshots & fixtures** — `__snapshots__`, `*.snap`, recorded HTTP cassettes (VCR),
  golden/approval files, reference screenshots.
- **Generated code** — `*.g.dart`, `*.pb.go`, `*_pb2.py`, sqlc/jOOQ/Ent output,
  `openapi`/`graphql` codegen, Prisma client, `dist/`, `build/`, minified bundles.
- **Vendored deps** and **pure moves/renames** (`git diff -M -C --stat` tells you which).

A `pod install` lockfile bump must not fake "large". Note the excluded files — the
*Reading order* section lists them under "Ignore". **Excluded ≠ unexamined:** whether a
generated artifact tracks the source change is part of what the change *does* — if the
schema moved and the generated client did not, the running code still sees the old shape,
and that is worth a line (see the Migration and Dependency lenses). A snapshot baseline
that changed is evidence about intent.

### Axis 1 — SIZE → lane (how much machinery)

| Lane | Trigger (on meaningful churn) | What changes vs Standard |
|---|---|---|
| **Fast** | ≤~3 meaningful files, single concern, low blast radius (no exported-signature / schema / auth / money change) | **Skip the parallel fan-out** (do a quick inline caller/test check instead). ≤1 diagram (skip if the flow is unchanged). 2–3 verify items. Still renders. |
| **Standard** | a normal PR | The full Steps 3–7 below, inline (fan out only if blast radius looks non-trivial). |
| **Deep** | ≥~10 meaningful files, OR crosses a boundary (client↔edge↔DB, new native module), OR high blast radius, OR touches migrations / auth / money | **Full parallel fan-out** (Step 5), old-vs-new diagrams, extra scrutiny, more verify items. |

When unsure between two lanes, pick the **larger** — under-reading a big PR is the
expensive mistake.

### Axis 2 — SCOPE → lens (which questions, which diagram, which sections)

Match the PR against the lenses below. **A PR may get one primary lens + secondary
lenses** (a feature that adds a migration is Feature × Migration). For each matched
lens, **read its file** and fold its guidance into the relevant steps:

| Lens | Fires when… | Lens file |
|---|---|---|
| **Visual / UI** *(previewable)* | view/style code — `*.tsx/jsx`, `*.vue`, `*.svelte`, templates, SwiftUI views, Compose, Flutter widgets, CSS/Tailwind/StyleSheet, design tokens; a screen split or navigation/IA reorganization; or the PR body has screenshots | `lenses/visual.md` |
| **Migration / schema** | `*.sql`, `**/migrations/**`, any migration toolchain (Prisma/Drizzle, Rails `db/migrate`, Django, Alembic, Flyway, Ecto), any DB DDL | `lenses/migration.md` |
| **Dependency bump** | only manifests + lockfiles change (`package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `Gemfile`, `Podfile`, `*.gradle`…) — versions, no app logic | `lenses/dependency.md` |
| **Refactor / no-behavior-change** | renames, moves, visibility changes, extractions, type-only edits; author *claims* no behavior change | `lenses/refactor.md` |
| **Feature / new flow** | new screens/routes/endpoints/jobs/files introducing behavior | `lenses/feature.md` |
| **Bugfix** | title/body says fix; small targeted change to existing logic | `lenses/bugfix.md` |
| **Config / CI / infra** | CI config (Actions, GitLab, CircleCI…), Dockerfiles, IaC (Terraform/Helm/k8s), env/secrets, build config | `lenses/config.md` |

If **nothing** matches cleanly, treat it as **Feature/Standard** and note the
ambiguity as the first *verify* item.

**Record the routing decision as a one-line `·`-separated string** — it is passed to
`--triage` in Step 8 and renders as header chips, so the user can falsify the triage
itself without it occupying the top of the report:
> Deep lane · Feature × Migration lens · 14 meaningful files (3 lockfile/snapshot ignored)

## Step 3 — "What this changes" (the opening section)

**This is the first section of the report**, and for most readers it is the only one they
read closely. Answer, in plain terms a reader can check against the code:

- **What** — what is different now. Describe the *mechanism*, not the goal: "adds
  `focus_metric` to the `persist` allowlist", not "improves persistence".
- **Why** — here intent is the point. Quote the author's stated reason when there is
  one, then say whether the code bears it out; otherwise reconstruct the reason from
  the code and say that you did.
- **How** — the shape of the change: which boundary moved, which file carries it.

Keep it to a few lines each, every claim anchored to a `file:line`. Then close the
section with a single **`>` callout** naming the one question that most needs a human
answer:

> **Check this first:** `Rate app` and the three social links are no longer reachable
> from Settings at all — only from Profile → Help & support
> (`components/Profile/HelpSupportEntry.tsx:20` is the sole entry point). Intended?

The callout **states the question; `## What's non-obvious` carries the evidence.**
Overlap with the first entry there is expected and fine — restate it in one or two
sentences here and develop it there. Do not move the evidence up, and do not
cross-reference by section name; the reader is two screens away from it.

Pick the callout by asking *"if the reviewer merges this without reading further, what
would I regret not having told them?"* — a behavior change the description doesn't
mention, a claim in the description the code doesn't bear out, a reach wider than the
title suggests. When the change holds no such question, say so outright; a callout that
manufactures alarm is worse than none.

**The architecture diagram (Step 6) belongs in this section** — it is the visual form of
*what* and *how*. Do not give it its own heading.

## Step 4 — Reading order

The reader knows what changed; now tell them where to point their eyes. Where to start,
what to ignore:
- **Load-bearing** — the 1–3 files where the actual behavior change lives. Start here.
- **Supporting** — files that follow from the load-bearing change.
- **Ignore** — Step 2's excluded set (generated, moved, renamed, pure-format churn) **plus
  anything else you can justify skipping**: a deletion of code that was already dead, five
  locale files that mirror one another, a rename with no body change. The test is "can I
  say why this is safe to skip", not "does it match a category". Say the why. **Omit the
  bucket entirely when nothing lands in it** — "Ignore: nothing" is filler.

**At ≥4 changed files, every one lands in exactly one bucket.** Count them against the
changed-file list — if the totals disagree, you dropped a file. Below that the reader can
see the whole list at a glance; just name the file to open first and move on. On a
two-file PR this section is a sentence, not a structure.

The load-bearing set also aims the next step: those are the symbols whose blast radius
matters most.

## Step 5 — Blast radius (lane-gated)

**Deep lane → fan out PARALLEL subagents.** One subagent each, dispatched together in a
single message so they run concurrently (whatever your harness calls the tool). Each
returns a compact `file:line` bullet list, no prose:

- **Callers** — for every exported/changed function, symbol, endpoint or RPC, who
  calls it, and which of those call sites the diff updated.
- **Tests** — which existing tests exercise the changed paths, and which of them the
  diff touched.
- **Type & schema usage** — every use site of changed types/interfaces/DB
  columns/API shapes, marking which the diff updated and which it did not.
- **Config / env / migration touch points** — new env vars, flags, migrations, or
  generated code this change implies.

**Standard lane →** fan out only if blast radius looks non-trivial; otherwise a quick
inline grep for callers + tests of the changed symbols is enough.

**Fast lane →** skip the fan-out; one inline look at who calls the changed symbol and
what covers it.

Merge into one **Blast radius** section. This section is a *map of reach*, not an
assessment: a use site the diff did NOT touch is the most useful thing here — the reader
will never see it in the patch — so name it, cite it, and say plainly that this change
reaches it. Stop there. Whether that is a problem is the reader's call to make, and the
reviewer's rail to argue. (Lenses add their own blast-radius targets, e.g. the Dependency
lens greps the changelog for breaking changes, not the repo.)

## Step 6 — Diagram the CHANGED flow (Mermaid)

**Lead with architecture.** The first diagram shows the change at the level of
*components and boundaries* — the modules/services/layers touched and how data crosses
between them. **It goes inside `## What this changes`** (Step 3), where it does the most
work. Only THEN, if a specific mechanism carries the weight, add a second, tighter
diagram — and put that one beside the observation it explains, not in a section of its
own. **The matched lens's `## Diagram` section picks the type — follow it.** Skip the
diagram entirely on the Fast lane when the flow is unchanged.

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

## Step 7 — "Verify these"

Restate the PR's implicit claims as **falsifiable questions the user checks against
the code** — count scales with the lane (Fast 2–3, Deep 5–7+), and **the lens's
`## Verify these (…)` section supplies its own**. Shape:
> "Claims the retry only fires on 5xx — verify at `api/client.ts:88` that a 4xx
> falls through without retrying."

**A verify item asks; it does not accuse** (hard rule 1). "Verify the down-migration
restores the data" is a question you are handing the reader. "The down-migration is
broken" is a verdict you are not entitled to and did not test — write the first, never
the second, even when you suspect the second.

Do not skip **trivial-looking edits that change behavior**: `||`→`??`, `===`→`==`, an
added `await`, a flipped default, a removed `!`. A one-character diff can be the whole PR.

## Step 8 — Render (and re-render on every revision)

### The skeleton is fixed — same H2s, same order, every PR

The renderer builds its contents nav from the H2s, so an ad-hoc structure produces a
nav the reader cannot learn. Use **exactly these headings, in this order**, and no
others at H2:

| # | H2 | From | Present |
|---|---|---|---|
| 1 | `## What this changes` | Step 3 (+ the architecture diagram) | always |
| 2 | `## Visual preview` | `lenses/visual.md` | Visual lens fires **and** it yields something to show |
| 3 | `## Reading order` | Step 4 | always |
| 4 | `## What's non-obvious` | your analysis | when there is something to report |
| 5 | `## Blast radius` | Step 5 | always |
| 6 | `## Verify these` | Step 7 | always |

**`## What's non-obvious` holds the observations that change the reader's model of the
change** — a consequence the diff does not show on its face (a prop that silently
discards a memoization), history that explains a surprising present state (three call
sites never got the newer helper because it was written after they were migrated), a
count the reader would otherwise have to assemble by hand. It is emphatically **not** a
defect list (hard rule 1): no verdict on quality, no "this is risky", no judgement about
whether the tests are adequate, no *"verified clean"*. Apply the litmus test to every
entry before it goes in. A PR that holds no surprises simply omits the section.

**All such entries live under that single H2**, one `###` each. The `###` is where
narrative headings belong — *"Three lists lost their no-recycling opt-out, because the
replacement was invented after they were migrated"* is a good `###` and a terrible H2.
Mechanism-level diagrams sit inside the `###` or the Blast radius subsection they
illustrate, never as their own section.

**A lens file's own `##` headings are instructions to you, not report sections.** Only
`## Visual preview` comes out of a lens as a section; everything else a lens tells you to
produce folds into the six above — its verify items into `## Verify these`, its reach
into `## Blast radius`, the rest into `## What's non-obvious` or the opening section.

Fenced ```mermaid for diagrams, deep-but-skippable content in
`<details><summary>…</summary>`. Then render and open it:

```bash
printf '%s' "$REPORT" | python3 "<this-skill-dir>/render.py" --title "PR #<n>" \
  --meta /tmp/pr-<n>-meta.json --triage "$TRIAGE"
# or pass a file: … --meta /tmp/pr-<n>-meta.json --triage "$TRIAGE" report.md
```

`--triage` takes the Step 2 line — `"Deep lane · Feature × Migration lens · 14 meaningful
files (3 ignored)"` — and renders each `·` part as a header chip. Always pass it; it is
how the triage stays falsifiable without occupying the top of the report.

`--meta` takes the Step 1 JSON **verbatim** and renders the identity bar under the title —
author + avatar, state, link back to the PR, dates, churn, branches — so the reader can
tell at a glance *which* change this map describes. Always pass it for a GitHub PR. With
no PR to point at (branch range, working tree), pass an inline JSON blob with whatever you
do know, or omit the flag:

```bash
--meta '{"author":{"name":"'"$(git log -1 --format=%an)"'"},"date":"'"$(git log -1 --format=%cI)"'","branch":"<head>","base":"<base>"}'
```

The title determines a **stable output path**, so **re-running updates the same artifact
in place**. Keep the title identical across re-renders of the same PR. The page is
ephemeral and lives in a temp dir — **commit nothing**.

**Rendering is the last action of every run.** If you change anything after the first
render, regenerate so the page is never stale, then report the path and **stop** — the
page is the deliverable, not a chat recap.
