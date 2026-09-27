---
name: pr-check
description: >
  Check the user's understanding of a pull request at three depths: a
  3-question consequence quiz (graded with --grade), corrections to a
  teach-back, or a drill (a Socratic back-and-forth), all pinned to the head SHA. Use when the user
  wants to test, or prove, that they understand a PR.
argument-hint: "<pr> [--depth quiz|teachback|drill] [--grade] [--lanes <lanes.json>]"
---

# PR check

Reading a diff feels like understanding it. This skill tests the feeling. It works the
same for the author and for a reviewer: the questions ask what the code now does, and
the code at the pinned SHA is the answer key.

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

## Quiz: `--depth quiz`, the default

**Budget:** 3 questions, one line each, each question at most 140 characters.

Write 3 **consequence** questions, each about what the code does in a case the diff
creates or changes: "What happens if `profile.units` is null now?", "Where does a user
land after a failed purchase?" At least one is a **why** question: it asks how the old
code failed, the failure this PR removes, answered at `$BASE`: "Before this PR, what
did a second tap on Place order do while the first order was still saving?" Each one:

- has one correct answer, provable from repo code with a `file:line`: at `$SHA`, or at
  `$BASE` for what the old code did, cited as `file:line@base`. Cite an absence by the
  range that lacks it (`file:12-40`) and the `git grep` that finds nothing;
- never turns on an unset library default (the answer would change if someone set an
  option the repo leaves unset) or on OS or scheduler timing (which widget entry the OS
  shows, when a background task runs). Fair game: the documented contract of a call the
  repo makes (an effect re-runs when a listed dependency changes), and language
  semantics (JS coercion, SQL `NULL` comparisons);
- asks about behaviour (null or empty input, errors, concurrency, old data, callers the
  diff left alone), never recall ("which file…", "what is the new function called");
- covers a different part of the change, starting with the load-bearing one. On Sat's
  own PR, favour cases the diff doesn't show on its face;
- asks nothing a pr-lanes reason states, before or after the PR: that card sits beside
  the quiz. Read pr-lanes' JSON pinned to `$SHA` from earlier in this conversation
  (Lucidos runs lanes → story → check in one session) or from `--lanes <file>`. With
  none, never quiz the change a lane reason would name (the unmentioned change, the one
  users see, the sensitive trigger); quiz its edges instead.

Line: `<id> — <question>`. Print the pin, the 3 lines, then
`Answer, then: /pr-check <n> --grade`. Keep the answers to yourself until grading.

```
pr-zone/przone-app#971 @ 3f9c2ab
3f9c2ab-q1 — A user misses a day while holding no freeze. What does streak_day() return for them now?
3f9c2ab-q2 — Before this PR, a user taps Use freeze twice in quick succession. What happens to their freeze count?
3f9c2ab-q3 — spend_freeze is called for a day that is already frozen. What does the user's freeze count do?
Answer, then: /pr-check 971 --grade
```

```json
{
  "schema": "pr-skills/check/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "mode": "quiz",
  "questions": [
    {"id": "3f9c2ab-q1", "question": "A user misses a day while holding no freeze. What does streak_day() return for them now?"},
    {"id": "3f9c2ab-q2", "question": "Before this PR, a user taps Use freeze twice in quick succession. What happens to their freeze count?"},
    {"id": "3f9c2ab-q3", "question": "spend_freeze is called for a day that is already frozen. What does the user's freeze count do?"}
  ]
}
```

A question `id` is `<sha7>-q<n>`, so an answer names the code it was asked about.

## Grade: `--grade`

**Budget:** 3 lines, one per question.

Input: Sat's answers, plus the quiz, either the quiz JSON block earlier in this
conversation or a quiz JSON passed with the answers (how Lucidos calls it).

Grade against the quiz's `head_sha`, not the PR's current head: acquire at that SHA.
Then compare it with the current `headRefOid`. If they differ, print
`Stale: PR moved <quiz sha7> → <head sha7> since the quiz; graded against <quiz sha7>.`
right after the pin (outside the budget) and set `"stale": true`.

Line: `<id> correct|partial|wrong — <correction> (<file:line>)`, `@base` marking old
code, an absence cited as in the quiz. A correct answer's evidence is its correction.

```json
{
  "schema": "pr-skills/check/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<quiz 40-hex>"},
  "generated_at": "2026-09-27T09:31:00Z",
  "mode": "grade",
  "current_head": "<40-hex>",
  "stale": false,
  "grades": [
    {"id": "3f9c2ab-q1", "verdict": "partial", "correction": "It resets to 0, but only at the user's local midnight, not UTC", "evidence": "supabase/functions/streak.ts:57"}
  ]
}
```

`pr.head_sha` is the SHA graded against; `verdict` is `correct|partial|wrong`.

## Teach-back: `--depth teachback`

**Budget:** at most 5 corrections, one line each.

Input: Sat's free-text explanation of the PR. None given: print
`Explain the PR in your own words: /pr-check <n> --depth teachback "<explanation>"` and stop.

Check every claim in the explanation against the diff at `$SHA`, then list:

- **wrong**: a claim the code contradicts. Quote it, and cite the line that shows otherwise.
- **missing**: a load-bearing part of the change the explanation leaves out.

Wrong before missing, and within each, by how much of the change it covers. Accurate
and complete: `Holds: nothing wrong, nothing load-bearing missing.`

Line: `<kind> — <correction> (<file:line>)`

Done when every claim in the explanation was checked, and every load-bearing hunk was
either covered by it or listed as missing.

```json
{
  "schema": "pr-skills/check/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:40:00Z",
  "mode": "teachback",
  "corrections": [
    {"kind": "wrong", "claim": "freezes are spent automatically", "text": "the user spends one by hand from FreezeSheet; nothing auto-spends", "evidence": "app/streak/FreezeSheet.tsx:22"}
  ]
}
```

`kind` is `wrong|missing`; `claim` is `null` for `missing`.

## Drill: `--depth drill`

A Socratic back-and-forth, chat-only, with no JSON block. "Drill" is the name
everywhere (flag, events, UI).

**Budget:** per turn, at most one sentence of feedback on the last answer, plus one
question of at most 2 sentences.

Pin the SHA in the first message. Questions follow the quiz rules; open with one on the
load-bearing change. Build each next question on the last answer: dig into a wrong or
partial one, or follow the flow one step further from a right one. Stop after 5
questions, or when Sat says so, with one line naming the weakest spot.
