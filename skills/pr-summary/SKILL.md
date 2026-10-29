---
name: pr-summary
description: >
  Say what a pull request does and how it does it, in plain words readable in
  about 15 seconds: one outcome, 2 to 5 mechanism steps, and the files that
  carry the change, all read from the diff. Use when asked what a PR does, or
  for a quick read before going deeper.
argument-hint: "<pr>"
---

# PR summary

The other pr-* skills go deep. This one is the 15-second read before them: what
changes once the PR merges, how it gets there, and where to look. PR bodies go stale
or stay empty, so the body is a hint and the diff is the truth.

## Ground rules, shared by all seven pr-* skills

- **Optional.** Nothing here gates a review or a merge; skipping this skill is always fine.
- **Sat acts alone.** Every next step you name is one the user (Sat) can take by
  themselves. On someone else's PR, work only from what already exists: the diff, the
  PR description, the linked ticket and git history. Never suggest asking the author.
- **Read-only.** No comments, reviews, labels, approvals, pushes, commits, checkouts or
  branch changes. No browser, database or running service, not even a read-only
  `SELECT`: no `psql`, no local Supabase or Docker stack. Read with `gh pr view|diff`,
  `gh issue view`, `gh api` GETs, `git fetch` (it adds objects, moves no branch),
  `git show|log|diff|grep|blame|ls-tree|merge-base|config`, `jq`, `mktemp`, `wc`, `date`
  and pr-recall's `python3 store.py`. Scratch files go under `/tmp`; pr-recall's card
  store is the only thing any pr-* skill writes.
- **Budgeted.** The budget is a ceiling, not a target: cut to fit. A line stays one
  line, never sub-bullets or a continuation. Each free-text field (a reason, question,
  claim, fact, correction) is at most 140 characters, in the text and in the JSON.
- **Pinned.** Resolve the head SHA once and compute everything against it. Open with
  the pin line `<owner>/<repo>#<n> @ <sha7>`, outside the budget.
- **Two outputs.** Plain text for Claude Code, then exactly one fenced `json` block with
  the same content, nothing extra, for the Lucidos Pulls app and review-prep rail to store.

## Budget

`what` in 1 or 2 sentences, at most 200 characters (the one field over 140). `how` in
2 to 5 steps, each under about 25 words. `where` in at most 4 files. Nothing else.

## Acquire

Input: a PR number in the current repo, `owner/repo#n`, or a PR URL. Pass it to
`gh pr` as `-R <owner/repo> <n>`: gh reads `owner/repo#n` as a branch name. For a
bare number, `<owner/repo>` is `gh repo view --json nameWithOwner -q .nameWithOwner`.

```bash
gh pr view -R <owner/repo> <n> --json number,url,title,body,headRefOid,baseRefOid,baseRefName,files,additions,deletions   # its headRefOid, baseRefOid, baseRefName are <sha>, <base-oid>, <base-ref>; resolve ONCE: FETCH_HEAD is overwritten by any later fetch
git fetch origin refs/pull/<n>/head <base-ref>
git merge-base <base-oid> <sha>   # prints <base>: the before-state
git diff --stat -M <base> <sha>   # the changed files, renames shown as renames
git diff -M <base> <sha> -- <path>   # one file's net diff; read the files that carry the change
git show <sha>:<path>; git grep -n '<symbol>' <sha>   # read the head without checking it out
```

- **Literals only.** No `$(...)`, backticks, variables or `export`: they die between
  tool calls, and a permission guard refuses substitution. Run each command alone, read
  its output, and paste the value into the next command as a literal (`<sha>`, `<base>`
  above).
- **No scratch files.** The budget is small enough to read every command's output
  directly: no redirects, no temp dir.
- `repo` in the JSON is `owner/name`, taken from the PR URL.
- **Not cloned locally** (or `origin` is another repo): read the diff with
  `gh pr diff -R <owner/repo> <n>` (the net diff; `--patch` is a per-commit series that
  repeats files), and files with
  `gh api "repos/<owner/repo>/contents/<path>?ref=<sha>" -H 'Accept: application/vnd.github.raw'`.
- **Can't read the PR** (gh fails, the PR doesn't exist, no access): emit the error
  JSON from Output and stop.

## Step 1 — Read the diff

- Read the diff before the body. The body may name the goal; only the code says what
  happens. Where they disagree, the code wins, and the summary never repeats a claim
  the diff doesn't back.
- Skip what carries no change: tests, lockfiles, generated code, snapshots, fixtures,
  vendored deps. Read them only to settle what a carrying file does.
- Find the carrying files: the ones a reader must see to understand the change. Usually
  the entry point (a route, screen, job, command) and the logic it calls.
- Pure renames, formatting or dependency bumps: note which, and stop reading.

Done when you can name the outcome and the mechanism, each traced to lines in the diff.

## Step 2 — Write it

Sat's standing preferences for this text:

- Plain words, no jargon, no filler, no em dashes. Short sentences.
- **`what`** is the outcome first, for the user or the codebase: "Users can now ...",
  "The workout screen no longer ...", "Streak math now lives in one hook". Never
  "This PR ...".
- **`how`** is the mechanism in order, not a file-by-file changelog. Each step is one
  plain sentence naming the main mechanism and the file or area it lives in.
- **`where`** holds at most 4 files that carry the change, each with a few words on what
  changed there. Never tests, lockfiles or generated files.
- Pure renames, formatting or dependency bumps: say so plainly in `what` ("Renames
  `useStreak` to `useStreakDays`; no behaviour changes.") and keep `how` to one step.
- Never invent behaviour the diff doesn't show. A step you can't trace to a line is cut.

## Output

```
pr-zone/przone-app#971 @ 3f9c2ab
What: Users can spend a streak freeze to keep a streak alive through one missed day.
How:
1. A new POST /streaks/freeze endpoint in api/streaks.ts takes one freeze from the user's balance.
2. The daily streak job skips the reset for a day that has a freeze on it.
3. The streak screen adds a Use freeze button that calls the endpoint and refreshes the count.
Where: api/streaks.ts (new freeze endpoint) · jobs/streakReset.ts (skips frozen days) · app/screens/Streak.tsx (Use freeze button)
```

```json
{
  "schema": "pr-skills/summary/v1",
  "status": "ok",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "title": "Streak freezes", "head_sha": "<40-hex>"},
  "what": "Users can spend a streak freeze to keep a streak alive through one missed day.",
  "how": [
    "A new POST /streaks/freeze endpoint in api/streaks.ts takes one freeze from the user's balance.",
    "The daily streak job skips the reset for a day that has a freeze on it.",
    "The streak screen adds a Use freeze button that calls the endpoint and refreshes the count."
  ],
  "where": [
    {"path": "api/streaks.ts", "role": "new freeze endpoint"},
    {"path": "jobs/streakReset.ts", "role": "skips frozen days"},
    {"path": "app/screens/Streak.tsx", "role": "Use freeze button"}
  ]
}
```

Can't read the PR: print `<owner>/<repo>#<n>: <reason>` and emit only

```json
{"schema": "pr-skills/summary/v1", "status": "error", "reason": "gh: Could not resolve to a PullRequest with the number of 9710"}
```

`status` is `ok|error`. With `ok`, every field above is present: `how` holds 2 to 5
strings (1 for a pure rename, formatting or dependency PR), `where` 1 to 4 objects
with repo-relative `path`. With `error`, only `schema`, `status` and `reason` are
required.
