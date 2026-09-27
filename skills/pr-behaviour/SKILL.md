---
name: pr-behaviour
description: >
  List what a pull request changes for its users as at most 5 before → after
  lines, paired with screenshots when a caller supplies them. Use when asked
  what users will notice, or what a PR looks like.
argument-hint: "<pr> [--shots <json>]"
---

# PR behaviour

What the PR does to the person using the product, not to the code. Every change is a
difference between two states you have read: the before-state at the merge base and
the after-state at the head.

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

At most 5 changes, one line each.

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

## Step 1 — Find the user-visible changes

A change is user-visible when someone using the product, or calling its public API or
CLI, could notice it: layout, copy, states (loading, empty, error), navigation and what
is reachable from where, notifications and emails, timing, permissions, the data shown
(formatting, rounding, sort order), public API responses, CLI output. Refactors,
logging and tests are internal.

For each candidate, read both sides: `git show "$BASE:<path>"` and `git show "$SHA:<path>"`.
A `+` line alone shows the after-state, not the change.

Line: `<surface>: <before> → <after> (<file:line>)`, e.g.
`Settings › Units: toggle lived under Profile → moved to the Settings root (SettingsScreen.tsx:84)`

More than 5: keep the ones that reach the most users, and put the omitted count in
`more`. None: print `No user-visible change.`

Done when every changed UI, copy, API and CLI file was read at both `$BASE` and `$SHA`.

## Screenshots: an optional hook

Capture needs a simulator or a browser, so it is the caller's job, never this skill's.
The hook meets capture tooling halfway, in both directions:

- **Out.** The JSON `capture` list names each visual surface and the state to shoot it
  in, so a caller with tooling (a repo script, a Lucidos rail) can shoot `$BASE` and
  `$SHA`. If the repo already carries capture tooling (Maestro flows, Playwright
  screenshots, fastlane snapshot, a `*screenshot*` script), name it in `capture_tool`.
- **In.** `--shots '<json>'` takes `[{"surface", "before", "after"}]` image paths or URLs
  from that caller. Each pair attaches to the change with the same surface. Before and
  after images already embedded in the PR description attach the same way, by URL.

With no shots, the text lines are the whole output.

## Output

```
pr-zone/przone-app#971 @ 3f9c2ab
Streak card: a missed day resets the streak → a held freeze is spent and the streak survives (streak.ts:57)
Streak card: no badge → frozen days show a snowflake badge (StreakCard.tsx:31)
Settings › Units: toggle lived under Profile → moved to the Settings root (SettingsScreen.tsx:84)
```

```json
{
  "schema": "pr-skills/behaviour/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "changes": [
    {"surface": "Streak card", "before": "no badge", "after": "frozen days show a snowflake badge", "evidence": "app/streak/StreakCard.tsx:31",
     "shots": {"before": "/tmp/shots/base/streak-card.png", "after": "/tmp/shots/head/streak-card.png", "source": "caller"}}
  ],
  "more": 0,
  "capture": [
    {"surface": "Streak card", "where": "Home tab", "state": "signed in, 5-day streak, one freeze held, yesterday missed"}
  ],
  "capture_tool": ".maestro/"
}
```

`shots` is `null` when none are attached; `source` is `caller|pr_body`. `capture_tool`
is `null` when the repo has none.
