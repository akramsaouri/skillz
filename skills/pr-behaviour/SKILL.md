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

## Ground rules, shared by all six pr-* skills

- **Optional.** Nothing here gates a review or a merge; skipping this skill is always fine.
- **Sat acts alone.** Every next step you name is one the user (Sat) can take by
  themselves. On someone else's PR, work only from what already exists: the diff, the
  PR description, the linked ticket and git history. Never suggest asking the author.
- **Read-only.** No comments, reviews, labels, approvals, pushes, commits, checkouts or
  branch changes. No browser, database or running service, not even a read-only
  `SELECT`: no `psql`, no local Supabase or Docker stack. Read with `gh pr view|diff`,
  `gh issue view`, `gh api` GETs, `git fetch` (it adds objects, moves no branch),
  `git show|log|diff|grep|blame|ls-tree|merge-base|config`, `jq`, `mktemp`, `wc` and
  pr-recall's `python3 store.py`. Scratch files go under `/tmp`; pr-recall's card store
  is the only thing any pr-* skill writes.
- **Budgeted.** The budget is a ceiling, not a target: cut to fit. A line stays one
  line, never sub-bullets or a continuation. Each free-text field (a reason, question,
  claim, fact, correction) is at most 140 characters, in the text and in the JSON.
- **Pinned.** Resolve the head SHA once and compute everything against it. Open with
  the pin line `<owner>/<repo>#<n> @ <sha7>`, outside the budget.
- **Two outputs.** Plain text for Claude Code, then exactly one fenced `json` block with
  the same content, nothing extra, for the Lucidos Pulls app and review-prep rail to store.

## Budget

At most 5 changes, one line each.

## Acquire

Input: a PR number in the current repo, `owner/repo#n`, or a PR URL. Pass it to
`gh pr` as `-R <owner/repo> <n>`: gh reads `owner/repo#n` as a branch name. For a
bare number, `<owner/repo>` is `gh repo view --json nameWithOwner -q .nameWithOwner`.

```bash
T=$(mktemp -d /tmp/pr-<n>.XXXXXX); echo "$T"   # one dir per run; reuse this path: shell variables die between tool calls
gh pr view -R <owner/repo> <n> --json number,url,title,body,author,state,mergedAt,headRefName,headRefOid,baseRefOid,baseRefName,files,additions,deletions,closingIssuesReferences > "$T/pr.json"
SHA=$(jq -r .headRefOid "$T/pr.json")   # resolve ONCE: FETCH_HEAD is overwritten by any later fetch
gh pr diff -R <owner/repo> <n> > "$T/pr.diff"   # the net diff; --patch is a per-commit series that repeats files
git fetch origin "refs/pull/<n>/head" "$(jq -r .baseRefName "$T/pr.json")"
BASE=$(git merge-base "$(jq -r .baseRefOid "$T/pr.json")" "$SHA")   # the before-state
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

## Step 1 — Find the user-visible changes

A change is user-visible when someone using the product, or calling its public API or
CLI, could notice it: layout, copy, states (loading, empty, error), navigation and what
is reachable from where, notifications and emails, timing, permissions, the data shown
(formatting, rounding, sort order), public API responses, CLI output. Refactors,
logging and tests are internal.

For each candidate, read both sides: `git show "${BASE}:<path>"` and `git show "${SHA}:<path>"`.
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
