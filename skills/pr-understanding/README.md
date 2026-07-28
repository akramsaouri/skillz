# pr-understanding

A Claude Code skill that helps you **understand** a pull request instead of
skimming a summary. Understanding is the bottleneck when AI writes the code — this
skill produces a *map you can falsify at a glance*, not prose you have to trust.

It **triages first** so a one-line fix, a UI tweak, a DB migration, and a 40-file
feature each get the right depth and the right questions — not one generic treatment.

## What it outputs

One **ephemeral HTML page** (temp dir, auto-opened, nothing committed) that opens with
a **Triage line** (the lane + lens it chose, so you can falsify the routing itself),
then:

1. **Blast radius** — callers, tests, type/schema uses, and config/migration touch
   points. On the Deep lane these are gathered by **parallel subagents**; on smaller
   PRs it's a lighter inline check. What the diff did NOT touch but should have is flagged.
2. **Reading order** — the load-bearing files to start with, and what to ignore.
3. **A Mermaid diagram of the changed flow** — old path vs new path when behavior
   changes. The lens picks the diagram type (ER for migrations, layout/style for
   visual, often none for dependency bumps).
4. **Standing checks** — repo-aware invariants (the highest-leverage part; see
   TUNE below) **plus lens-specific checks** (RLS for migrations, dark-mode/a11y for
   visual, leaked-secret for config…).
5. **Verify these** — the PR's implicit claims rewritten as falsifiable questions
   with `file:line`, count scaled to the lane.
6. **Lens-specific sections** — e.g. a **Visual preview** (author screenshots, changed
   image assets, or a style-delta table), a migration safety read, a dependency
   changelog → call-site match.

It never emits a prose "what this PR does" paragraph — that is the whole point.

## How triage works (two orthogonal axes)

Step 2 fingerprints the PR from `--stat`, file paths, and content signals, then sets
two independent dials. Size is measured on **meaningful churn** — lockfiles, snapshots,
and generated code are excluded, so a `pod install` lockfile bump doesn't fake "large".

**Axis 1 — SIZE → lane** (how much machinery):

| Lane | Trigger | Effect |
|---|---|---|
| **Fast** | ≤~3 meaningful files, single concern, low blast radius | skip the parallel fan-out, ≤1 diagram, 2–3 verify items |
| **Standard** | a normal PR | the full process, fan out only if blast radius is non-trivial |
| **Deep** | ≥~10 files, crosses a boundary, high blast radius, or touches migrations/auth/money | full parallel fan-out, old-vs-new diagrams, widest scrutiny |

**Axis 2 — SCOPE → lens** (which questions/diagram/checks/sections). A PR can get a
primary lens **plus** secondaries (a feature that adds a migration is Feature ×
Migration). Each lens is its own file under `lenses/`, loaded **only when it matches**,
so the base prompt stays small and you can add archetypes without bloating it:

| Lens | Fires when… |
|---|---|
| **Visual / UI** | view/style files change, or the PR body has screenshots |
| **Migration / schema** | SQL / migrations / ORM schema / DDL |
| **Dependency bump** | only manifests + lockfiles change |
| **Refactor** | renames/moves/de-exports; author claims no behavior change |
| **Feature / new flow** | new screens/routes/endpoints introducing behavior |
| **Bugfix** | a targeted fix to existing logic |
| **Config / CI / infra** | `.github/`, CI yaml, Dockerfiles, env/secrets |

## Install

Global (all repos):
```
~/.claude/skills/pr-understanding/{SKILL.md,render.py,README.md,lenses/*.md}
```
Per-repo (overrides global, lets you commit repo-specific standing checks and lenses):
```
<repo>/.claude/skills/pr-understanding/
```

Then in Claude Code: **"understand PR #123"** (or "explain this diff"). The
`description` field auto-triggers the skill.

## Tune it — standing checks (do this)

The generic skill is fine; the *valuable* skill is repo-aware. Open `SKILL.md`,
find the `<!-- TUNE -->` block in **Step 6**, and replace it with the invariants
that always matter in your repo. Examples:

- **Supabase / RLS**: does every changed RPC still enforce row-level security?
- **Anything with money**: are all amounts still in minor units (no float leak)?
- Timestamps stored UTC, formatted local only at the edge?
- New external call without a timeout / error path?
- Secret, token, or PII newly logged?

A per-repo copy is the natural home for these, since they differ per codebase. You can
also add per-repo lenses (drop a file in `lenses/` and reference it from the Step 2
table) or override a shipped lens with a repo-specific version.

## Add a lens

A lens is a plain markdown file under `lenses/` with sections that map onto the SKILL
steps: **preview/read strategy**, **diagram type**, **standing checks**, **verify
these**. Add a row to the Step 2 SCOPE table in `SKILL.md` pointing at it. The skill
reads a lens file only when the triage matches it, so the cost of having many lenses is
zero until one fires.

## Pairs well with Layer 0 — difftastic

Run a structural (AST) diff first so renames, reindents, and moved blocks stop
reading as "changes". Less non-signal reaches the skill (the **Refactor** lens leans on
this directly):

```
brew install difftastic
git config --global diff.external difft   # or use: GIT_EXTERNAL_DIFF=difft git diff
```

## Gotchas it handles for you

- **Net diff, not the commit series.** It uses `gh pr diff <n>` (no `--patch`) so a file
  touched by several commits, or a rename, shows **once** — not two/three noisy blocks.
- **Merged / closed PRs.** The head branch is usually deleted, so `git fetch origin <head>`
  fails. It falls back to the merge commit: `git diff "$SHA^" "$SHA"` where
  `SHA = gh pr view <n> --json mergeCommit -q .mergeCommit.oid`.
- **SSH-only clones.** Uses `gh repo clone` / `gh pr checkout` (token auth) instead of a
  plain `git clone https://…`, which fails when git is configured for SSH.
- **Fake "large" PRs.** Lockfiles, snapshots, and generated code are excluded from the
  size measurement, so a dependency bump or codegen churn doesn't get the Deep-lane
  treatment it doesn't need.

## Requirements

- `gh` CLI (to fetch PRs) or a git repo (for `git diff`).
- Python 3 (stdlib only — `render.py` has zero pip dependencies).
- A browser + network at view time (Markdown/Mermaid load from pinned CDN ESM
  builds; offline, the page degrades to raw markdown).
