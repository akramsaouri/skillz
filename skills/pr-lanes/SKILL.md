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
- **Budgeted.** The budget is a ceiling, not a target: cut to fit. A line stays one
  line, never sub-bullets or a continuation. Each free-text field (a reason, claim,
  fact, correction) is at most 140 characters, in the text and in the JSON.
- **Pinned.** Resolve the head SHA once and compute everything against it. Open with
  the pin line `<owner>/<repo>#<n> @ <sha7>`, outside the budget.
- **Two outputs.** Plain text to read in Claude Code, then exactly one fenced `json`
  block for the Lucidos Pulls app and review-prep rail: the same content, nothing
  extra. The caller stores the JSON; this skill writes no file.

## Budget

At most 3 recall lines, then one line per lane. Nothing else.

## Acquire

Input: a PR number in the current repo, `owner/repo#n`, or a PR URL.

```bash
gh pr view <pr> --json number,url,title,body,author,state,mergedAt,headRefOid,baseRefOid,baseRefName,files,additions,deletions,closingIssuesReferences > /tmp/pr-<n>.json
SHA=$(jq -r .headRefOid /tmp/pr-<n>.json)   # resolve ONCE: FETCH_HEAD is overwritten by any later fetch
gh pr diff <pr> > /tmp/pr-<n>.diff            # the net diff; --patch is a per-commit series that repeats files
git fetch origin "refs/pull/<n>/head" "$(jq -r .baseRefName /tmp/pr-<n>.json)"
BASE=$(git merge-base "$(jq -r .baseRefOid /tmp/pr-<n>.json)" "$SHA")   # the before-state
git show "$SHA:<path>"; git grep -n '<symbol>' "$SHA"   # read the head without checking it out
```

- `repo` in the JSON is `owner/name`, taken from the PR URL.
- **Own PR**: `author.login` equals `gh api user -q .login`.
- **Not cloned locally** (or `origin` is another repo): read files with
  `gh api "repos/<owner>/<repo>/contents/<path>?ref=$SHA" -H 'Accept: application/vnd.github.raw'`
  and history with `gh api "repos/<owner>/<repo>/commits?path=<path>"`.

## Step 1 — Recall

Run pr-recall's **Match** procedure (`<this-skill-dir>/../pr-recall/SKILL.md`, section
"Match") on this PR. Keep at most 3 hits, ordered `no` → `unclear` → `yes`. No store,
or no card overlaps: print no recall lines.

`✗ decision · #812 — Streak days are computed server-side — useStreak.ts:41 recomputes them on the client`

`✗` no, `?` unclear, `✓` yes.

## Step 2 — Signals

Read these from the metadata and the diff. They are also the JSON `signals`.

- **Meaningful files**: changed files minus lockfiles, snapshots and fixtures, generated
  code (codegen output, `dist/`, `build/`), vendored deps, and pure renames.
- **Areas**: distinct top-level modules among the meaningful files (the first path
  segment, or the second under `src/`, `app/`, `packages/`).
- **New abstractions**: added exported types, classes, interfaces, protocols, hooks,
  services, tables or modules.
- **Author**: `own`, `other`, or `bot` (`dependabot`, `renovate`, a `[bot]` login).
- **Ticket**: a closing issue, or a ticket key or URL in the title, body or branch
  name; else `null`.
- **Sensitive**: which of `ui`, `schema`, `money` (billing, payments, IAP, prices) and
  `auth` (sessions, tokens, permissions, RLS) the diff touches.
- **Familiarity**: Sat's commits in the touched paths over the last year,
  `git log --since=1.year --author="$(git config user.email)" --oneline "$SHA" -- <paths> | wc -l`.

## Step 3 — Lanes

Test every lane against its trigger and tag each one that holds, in table order.

| Lane | Fires when | Next |
|---|---|---|
| intent | the PR adds behaviour: a new route, screen, endpoint, job, flag or exported capability | `/pr-intent` |
| structure | ≥3 areas, ≥10 meaningful files, a move or refactor at scale, or new abstractions | `/pr-story` |
| behaviour | a user can notice it: UI, copy, navigation, notifications, errors, public API or CLI output | `/pr-behaviour` |
| understanding | touches a sensitive area or the core domain, familiarity ≤2, or an exported symbol with many callers changes | `/pr-check` |
| remember | it sets a decision, invariant or convention later PRs will lean on, moves something people look for, or a recall hit reads `no` | `/pr-recall create` once merged |
| trust | every meaningful change is mechanical: version bumps, lockfiles, generated code, formatting, renames, config with no app logic | none |

- **trust is exclusive.** It fires only when no other lane does. A PR with zero
  meaningful files is trust.
- On Sat's own PR, the intent line's next step is `/pr-intent <n> "<your why>"`.
- A reason names evidence Sat can check: "adds `POST /streaks/freeze` (api/streaks.ts)
  for ticket PZ-88", not "adds a feature".

Line: `<lane> — <reason> → <next>`

Done when all six lanes were tested, and each tagged lane has exactly one line.

## Output

```
pr-zone/przone-app#971 @ 3f9c2ab
✗ decision · #812 — Streak days are computed server-side — useStreak.ts:41 recomputes them on the client
intent — adds POST /streaks/freeze (api/streaks.ts) for ticket PZ-88 → /pr-intent
understanding — spends an IAP entitlement in purchase.ts; Sat has 0 commits there this year → /pr-check
remember — reverses #812: streak days move to the client → /pr-recall create once merged
```

```json
{
  "schema": "pr-skills/lanes/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "own": false,
  "recall": [
    {"card_id": "pr-zone/przone-app#812-1", "pr": 812, "kind": "decision", "fact": "Streak days are computed server-side", "still_true": "no", "why": "useStreak.ts:41 recomputes them on the client"}
  ],
  "lanes": [
    {"lane": "intent", "reason": "adds POST /streaks/freeze (api/streaks.ts) for ticket PZ-88", "next": "pr-intent"},
    {"lane": "understanding", "reason": "spends an IAP entitlement in purchase.ts; Sat has 0 commits there this year", "next": "pr-check"},
    {"lane": "remember", "reason": "reverses #812: streak days move to the client", "next": "pr-recall"}
  ],
  "signals": {"meaningful_files": 14, "ignored_files": 3, "areas": ["api", "app"], "new_abstractions": 2, "author": "other", "ticket": "PZ-88", "sensitive": ["money"], "familiarity": 0}
}
```

`lane` is one of `intent|structure|behaviour|understanding|remember|trust`; `next` is
the skill name, or `null` for trust. `still_true` is `yes|no|unclear`.
