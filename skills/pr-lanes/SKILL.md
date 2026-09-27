---
name: pr-lanes
description: >
  Triage a pull request into review lanes (intent, structure, behaviour,
  understanding, remember, trust), one-line reason each, and surface the
  pr-recall cards it touches. Use as the first pass on a PR, or to pick which
  pr-* skill to run next.
argument-hint: "<pr>"
---

# PR lanes

The router. Tag the PR with every lane that fits, one line each, so Sat sees which
of the other pr-* skills are worth running on it, and which PRs need nothing at all.
Past decisions the PR touches go on top: a PR that quietly undoes one is the most
expensive thing to miss.

## Ground rules

Shared by all six pr-* skills.

- **Optional.** Nothing here gates a review or a merge; skipping this skill is always fine.
- **Sat acts alone.** Every next step you name is one the user (Sat) can take by
  themselves. On someone else's PR, work only from what already exists: the diff, the
  PR description, the linked ticket and git history. Never suggest asking the author.
- **Read-only.** Toward GitHub and every repo: no comments, reviews, labels, approvals,
  pushes, commits, checkouts or branch changes, and never a browser. Use `gh` and `git`
  read commands only: `gh pr view|diff`, `gh issue view`, `gh api` GETs,
  `git show|log|diff|grep|blame|ls-tree|merge-base`, and `git fetch` (it adds objects
  and moves no local branch). Scratch files under `/tmp` are fine. pr-recall's card
  store is the only thing any pr-* skill writes.
- **Git and gh only.** Never query a database or a running service, not even a
  read-only `SELECT`: no `psql`, no local Supabase or Docker stack, no running app.
- **Budgeted.** The budget is a ceiling, not a target: cut to fit. A line stays one
  line, never sub-bullets or a continuation. Each free-text field (a reason, question,
  claim, fact, correction) is at most 140 characters, in the text and in the JSON.
- **Pinned.** Resolve the head SHA once and compute everything against it. Open with
  the pin line `<owner>/<repo>#<n> @ <sha7>`, outside the budget.
- **Two outputs.** Plain text to read in Claude Code, then exactly one fenced `json`
  block for the Lucidos Pulls app and review-prep rail: the same content, nothing
  extra. The caller stores the JSON; only pr-recall writes a file, its card store.

## Budget

At most 3 recall lines (or the no-match line), then one line per lane (or the no-lane
line). Nothing else.

## Acquire

Input: a PR number in the current repo, `owner/repo#n`, or a PR URL. Pass it to
`gh pr` as `-R <owner/repo> <n>`: gh reads `owner/repo#n` as a branch name. For a
bare number, `<owner/repo>` is `gh repo view --json nameWithOwner -q .nameWithOwner`.

```bash
gh pr view -R <owner/repo> <n> --json number,url,title,body,author,state,mergedAt,headRefOid,baseRefOid,baseRefName,files,additions,deletions,closingIssuesReferences > /tmp/pr-<n>.json
SHA=$(jq -r .headRefOid /tmp/pr-<n>.json)   # resolve ONCE: FETCH_HEAD is overwritten by any later fetch
gh pr diff -R <owner/repo> <n> > /tmp/pr-<n>.diff   # the net diff; --patch is a per-commit series that repeats files
git fetch origin "refs/pull/<n>/head" "$(jq -r .baseRefName /tmp/pr-<n>.json)"
BASE=$(git merge-base "$(jq -r .baseRefOid /tmp/pr-<n>.json)" "$SHA")   # the before-state
git show "${SHA}:<path>"; git grep -n '<symbol>' "$SHA"   # read the head without checking it out
```

- **zsh-safe.** Brace a SHA before a colon, `"${SHA}:<path>"` and `"${BASE}:<path>"`:
  zsh reads `$SHA:h`, `:t`, `:r` and `:e` as modifiers (`hooks/x.ts` became `.ooks/x.ts`).
  Pass each path as its own quoted word: zsh never splits an unquoted `$VAR` into words.
- `repo` in the JSON is `owner/name`, taken from the PR URL.
- **Own PR**: `author.login` equals `gh api user -q .login`.
- **Not cloned locally** (or `origin` is another repo): read files with
  `gh api "repos/<owner/repo>/contents/<path>?ref=${SHA}" -H 'Accept: application/vnd.github.raw'`
  and history with `gh api "repos/<owner/repo>/commits?path=<path>"`.

## Step 1 — Recall

Run pr-recall's **Match** procedure (`<this-skill-dir>/../pr-recall/SKILL.md`, section
"Match") on this PR. Keep at most 3 hits, ordered `no` → `unclear` → `yes`. No store,
or no card overlaps: print `Recall: no matching cards`, the line Match prints too.

`✗ decision · #812 — Streak days are computed server-side — useStreak.ts:41 recomputes them on the client`

`✗` no, `?` unclear, `✓` yes.

## Step 2 — Signals

Read these from the metadata and the diff. They are also the JSON `signals`.

- **Trust-class files** (`ignored_files`) fire no lane: lockfiles, generated code,
  vendored deps, pure renames, formatting, version bumps, config with no app logic;
  docs, prose QA specs, specs that only move line numbers, translations, fixtures,
  snapshots; agent prompts, skills and hooks (`CLAUDE.md`, `.claude/`, `.agents/`)
  unless they change a gate: review, merge, auto-merge, release or a CI skip. A gate
  change is meaningful: it fires `behaviour` and is sensitive `gate`.
- **Meaningful files**: every other changed file. Only they fire lanes.
- **Areas**: of the meaningful files. An area is the first path segment, or the first
  two under `apps/`, `packages/`, `services/`, `libs/`, `src/`; a root file is `(root)`.
  `components/Workout/Pill.tsx` → `components`, `apps/web/page.tsx` → `apps/web`.
- **New abstractions**: symbols exported at `$SHA` and not at `$BASE` (types,
  functions, classes, components, hooks), plus new tables, RPCs, endpoints and jobs.
  Not unexported helpers, a new file as such, re-exports, tests, or a moved symbol.
- **Author**: `own`, `other`, or `bot` (`dependabot`, `renovate`, a `[bot]` login).
- **Ticket**: a closing issue, or a ticket key or URL in the title, body or branch
  name; else `null`.
- **Sensitive**: categories the meaningful lines alter, not just read, render or
  memoize; UI, copy and styling never count. `auth` (sessions, tokens, permissions,
  RLS), `money` (payments, prices, entitlements), `data` (deleting or migrating stored
  data), `security` (secrets, access, input validation), `concurrency` (races, locks,
  retries, ordering), `contract` (an API, schema or export existing callers rely on),
  `gate` (review, merge, release, CI skip, in code or agent instructions).
- **Familiarity**: how well Sat knew each area before this PR. Count Sat's commits from
  `$BASE`, which leaves out this PR's own, one call per area with the area as one quoted
  word (`(root)` is `':(top,glob)*'`), and keep the lowest count with its area:
  `git log --since=1.year --author="$(git config user.email)" --format=%h "$BASE" -- 'widgets' | wc -l`

## Step 3 — Lanes

Test every lane against its trigger and tag each one that holds, in table order.

| Lane | Fires when | Next |
|---|---|---|
| intent | the PR adds a capability (a new route, screen, endpoint, job, flag or public API), or does something its title and body never mention; a fix or refactor alone is not intent | `/pr-intent` |
| structure | ≥3 areas, ≥10 meaningful files, ≥3 new abstractions, or a move or refactor at scale | `/pr-story` |
| behaviour | a user can notice it (UI, copy, navigation, notifications, errors, public API or CLI output), or it changes a gate | `/pr-behaviour` |
| understanding | `sensitive` is not empty, the least familiar area has ≤2 commits, or an export imported by ≥10 files at `$SHA` changes its signature, return shape or side effects | `/pr-check` |
| remember | it sets a decision, invariant or convention later PRs will lean on, moves something people look for, or a recall hit reads `no` | `/pr-recall create` once merged |
| trust | there are no meaningful files: every change is Trust-class | none |

- **trust is exclusive.** No meaningful files: print the trust line and no other lane,
  whatever the Trust-class changes say. Any meaningful file: trust never fires.
- No lane holds: print `No lane: nothing here needs another pr-* skill.`
- On Sat's own PR, the intent line's next step is `/pr-intent <n> "<your why>"`.
- A reason names evidence Sat can check: "adds `POST /streaks/freeze` (api/streaks.ts)
  for ticket PZ-88", not "adds a feature". An understanding reason names its trigger:
  the category, the area and its count, or the export and its importer count.

Line: `<lane> — <reason> → <next>`

Done when all six lanes were tested, and each tagged lane has exactly one line.

## Output

```
pr-zone/przone-app#971 @ 3f9c2ab
✗ decision · #812 — Streak days are computed server-side — useStreak.ts:41 recomputes them on the client
intent — adds POST /streaks/freeze (api/streaks.ts) for ticket PZ-88 → /pr-intent
understanding — money: spends an IAP entitlement in purchase.ts; Sat has 0 commits in api before this PR → /pr-check
remember — reverses #812: streak days move to the client → /pr-recall create once merged
```

```json
{
  "schema": "pr-skills/lanes/v2",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "own": false,
  "recall": [
    {"card_id": "pr-zone/przone-app#812-1", "pr": 812, "kind": "decision", "fact": "Streak days are computed server-side", "still_true": "no", "why": "useStreak.ts:41 recomputes them on the client"}
  ],
  "lanes": [
    {"lane": "intent", "reason": "adds POST /streaks/freeze (api/streaks.ts) for ticket PZ-88", "next": "pr-intent"},
    {"lane": "understanding", "reason": "money: spends an IAP entitlement in purchase.ts; Sat has 0 commits in api before this PR", "next": "pr-check"},
    {"lane": "remember", "reason": "reverses #812: streak days move to the client", "next": "pr-recall"}
  ],
  "signals": {"meaningful_files": 6, "ignored_files": 2, "areas": ["api", "app"], "new_abstractions": 2, "author": "other", "ticket": "PZ-88", "sensitive": ["money"], "familiarity": {"area": "api", "commits": 0}}
}
```

`lane` is one of `intent|structure|behaviour|understanding|remember|trust`; `next` is
the skill name, or `null` for trust. `still_true` is `yes|no|unclear`. `sensitive`
holds `auth|money|data|security|concurrency|contract|gate`; `familiarity` is `null`
with no meaningful files. **v2**: in v1, `sensitive` held `ui|schema|money|auth` and
`familiarity` was a bare number over every touched path, this PR's commits included.
