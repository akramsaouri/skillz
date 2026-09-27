---
name: pr-intent
description: >
  Check a pull request's "why" against its diff. On the user's own PR, challenge
  the why they wrote; on someone else's, draft one from the ticket and
  description with every guessed claim tagged [guess]. Use when asked why a PR
  exists, or whether it does what it says.
argument-hint: '<pr> ["<your why>"]'
---

# PR intent

A PR's stated reason and its code drift apart quietly: a "small fix" grows a second
change, a promised behaviour never lands. Put the why beside the diff and name every
place they disagree.

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

The why in at most 3 sentences, then at most 5 mismatches, one line each. A why Sat
typed as the argument is their input: show it verbatim, outside the budget.

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

## Step 1 — The why

**Own PR.** The why is Sat's, and you challenge it rather than write it.

- From the argument, verbatim.
- No argument: condense the PR description, which Sat wrote, to at most 3 sentences in
  their own words.
- Both empty: print `Write the why in up to 3 sentences: /pr-intent <n> "<why>"`, emit
  the JSON with `"status": "needs_why"`, and stop.

**Someone else's PR.** Draft at most 3 sentences, drawing on, in order of weight: the
linked ticket, the PR description, commit messages, then the code.

- Tag **[guess]** after every claim no text states, meaning one you inferred from the
  code alone. A claim the ticket or description states carries no tag; quote its
  source phrase in the JSON `from`.
- Ticket: `gh issue view` for a GitHub issue. A ticket in another tracker (Jira,
  Linear, Notion) counts only if a read-only CLI or MCP tool already on hand fetches
  it. Otherwise use what the PR text quotes of it, and tag claims resting on it [guess].
- Close with one line: `Challenge any claim: reply with it and why you doubt it.` When
  Sat does, re-check that claim against the diff and ticket, and answer in one line:
  kept (with the evidence), revised (with the new wording), or dropped.

## Step 2 — Mismatches

Compare the **stated** intent with the diff. On Sat's PR that is their why. On someone
else's it is the description plus the ticket, never your own [guess] claims.

- **unbacked**: the stated intent claims it, and no code does it. Quote the claim.
- **unstated**: the code does it, and the stated intent never mentions it. Cite
  `file:line`. Formatting, lockfiles and generated code don't count.
- **contradicts**: the code does something other than what is claimed. Quote the claim
  and cite the line.

Rank by how much of the diff each one covers and keep the top 5. None: print
`No mismatches: every change traces to the why, and every claim has code.`

Line: `<kind> — <what> (<file:line>)`

Done when every claim in the stated intent was checked against the code, and every
meaningful hunk was traced to a claim or listed as unstated.

## Output

```
pr-zone/przone-app#971 @ 3f9c2ab
Lets users spend a streak freeze to keep a streak alive through one missed day. Freezes cost 50 coins [guess]. Each user can hold at most two [guess].
Challenge any claim: reply with it and why you doubt it.
unstated — also drops the 24h grace window for every user, frozen or not (api/streaks.ts:88)
unbacked — "freezes show on the calendar" — no calendar file changes
```

```json
{
  "schema": "pr-skills/intent/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "own": false,
  "status": "ok",
  "why": {
    "source": "draft",
    "claims": [
      {"text": "Lets users spend a streak freeze to keep a streak alive through one missed day.", "guess": false, "from": "ticket PZ-88: \"spend a freeze to save a streak\""},
      {"text": "Freezes cost 50 coins.", "guess": true, "from": null}
    ]
  },
  "mismatches": [
    {"kind": "unstated", "claim": null, "text": "also drops the 24h grace window for every user, frozen or not", "evidence": "api/streaks.ts:88"},
    {"kind": "unbacked", "claim": "freezes show on the calendar", "text": "no calendar file changes", "evidence": null}
  ]
}
```

`status` is `ok|needs_why`. `why.source` is `user` (the argument), `description` (Sat's
PR body) or `draft`; on Sat's PR every claim has `"guess": false`. `kind` is
`unbacked|unstated|contradicts`.
