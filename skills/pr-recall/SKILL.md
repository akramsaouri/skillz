---
name: pr-recall
description: >
  Remember merged pull requests as 1–3 one-line cards on how the code works
  after the merge, and match an open PR against stored cards to flag one that
  undoes an earlier decision. Use after a PR the user reviewed merges (create),
  or to check an open PR against past decisions (match).
argument-hint: "create|match <pr>"
---

# PR recall

What a review taught evaporates at merge. A card keeps the one fact that will matter
the next time someone touches these files, and `match` checks every new PR against
those facts. That is how a PR that quietly undoes an earlier decision gets caught.

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
  extra. The caller stores the JSON; the card store is the only file this skill writes.

## Card

```json
{
  "id": "pr-zone/przone-app#812-1",
  "repo": "pr-zone/przone-app",
  "pr": 812,
  "head_sha": "<40-hex head at merge>",
  "merged_at": "2026-09-14T16:02:11Z",
  "files": ["supabase/functions/streak.ts", "app/hooks/useStreak.ts"],
  "symbols": ["streak_day", "useStreak"],
  "kind": "decision",
  "fact": "Streak days are computed server-side by streak_day() from the user's tz offset; the client only displays them"
}
```

- A card is a **statement** about how the code works after the merge, not a question
  and answer. It names at least one symbol or file, so it can be checked, and its
  `fact` is one line of at most 140 characters.
- `kind`:
  - **decision**: a choice among alternatives that the code now embodies.
  - **invariant**: something the code relies on staying true.
  - **moved**: something lives somewhere else now. `files` lists the old and new paths.
  - **gotcha**: a trap that isn't visible at the call site.
- `files` and `symbols` are the match keys: the paths and names a later PR would touch
  if it disturbed the fact.
- `id` is `<repo>#<pr>-<n>`, and `store.py` assigns it.

## Store

One JSON file, `{"schema": "pr-recall/cards/v1", "cards": [...]}`, holding the cards
for every repo. Its path is `$PR_RECALL_STORE`. When that is unset it defaults to
`$LUCIDOS_WORKSPACE/data/artifacts/pr-recall/cards.json`, the canonical store, a Lucidos
workspace artifact. With neither variable set there is no store.

Every read and write goes through `<this-skill-dir>/store.py`, never by hand. It
resolves the path; writes through `lucidos data write` when the `lucidos` CLI is on
PATH and the store sits inside the workspace's `data/` (a direct atomic file write
otherwise); replaces a PR's cards instead of appending duplicates; validates each card
against the schema and budget; and refuses to overwrite a store it cannot parse.

```bash
python3 <this-skill-dir>/store.py path                                             # exit 3 = no store
python3 <this-skill-dir>/store.py overlap --repo <owner/repo> < /tmp/pr-<n>.diff   # cards this diff touches
python3 <this-skill-dir>/store.py upsert --repo <owner/repo> --pr <n> < cards.json # replace this PR's cards
```

A refusal from `upsert` (exit 2) names the broken field: fix the card and re-run.

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

## Create: `create <pr>`

**Budget:** at most 3 cards, one line each: `<kind> · <fact>`.

**Scope.** Cards are made only for PRs Sat personally reviewed. The Lucidos rail makes
that call before it invokes `create`; invoked by hand, the invocation is Sat's word for
it. Take it as given.

1. Acquire. `state` must be `MERGED`. Otherwise print
   `#<n> is not merged; cards describe merged code.`, emit the JSON with
   `"status": "not_merged"`, and stop.
2. Pick 1 to 3 facts that will matter the next time someone touches these files.
   Prefer what a later PR could silently undo (a decision, an invariant) over what is
   merely new. Confirm each fact is true at `$SHA` by reading the line it rests on.
   When nothing outlives the merge (a pure dependency bump, formatting), make no card
   and say why in one line: a junk card costs every future match.
3. Pipe the cards, without `id`, to `store.py upsert`. It replaces any earlier cards for
   this PR, so re-running is safe. With no store, print the cards anyway, add
   `No store: set PR_RECALL_STORE to keep these.`, and set `store.written` to `false`.

```json
{
  "schema": "pr-skills/recall/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 812, "url": "https://github.com/pr-zone/przone-app/pull/812", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-14T16:40:00Z",
  "mode": "create",
  "status": "ok",
  "cards": [{"id": "pr-zone/przone-app#812-1", "...": "the card shape above"}],
  "store": {"path": "/…/data/artifacts/pr-recall/cards.json", "written": true, "via": "lucidos"}
}
```

`status` is `ok|not_merged`; `via` is `lucidos|file`, or `null` when nothing was written.

## Match: `match <pr>`

**Budget:** at most 5 lines: `✗|?|✓ <kind> · #<pr> — <fact> — <why>`. The JSON
carries every match.

1. Acquire, then `store.py overlap --repo <repo> < /tmp/pr-<n>.diff`. It returns the
   cards whose `files` the diff touches or whose `symbols` appear on its changed
   lines, each with `via` saying which.
2. Read each card's fact against the diff at `$SHA` and set `still_true`:
   - **yes**: the PR leaves the fact intact, for instance it edits the file but not the
     part the fact is about.
   - **no**: the diff makes the fact false. `why` cites the line.
   - **unclear**: the diff touches what the fact is about, but whether it still holds
     turns on something the diff doesn't show (runtime data, config, a caller outside
     the diff). `why` names that thing.
3. Order `no` → `unclear` → `yes`. No store, or no overlap: print `No stored card
   touches this PR.`

pr-lanes runs this procedure and keeps the top 3.

```json
{
  "schema": "pr-skills/recall/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "mode": "match",
  "matches": [
    {"card": {"id": "pr-zone/przone-app#812-1", "...": "the full card"}, "via": {"files": ["app/hooks/useStreak.ts"], "symbols": ["streak_day"]},
     "still_true": "no", "why": "useStreak.ts:41 now computes the streak day on the client from the device clock"}
  ]
}
```
