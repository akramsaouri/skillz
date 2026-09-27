---
name: pr-story
description: >
  Order a pull request's diff into a reading story (types, data, logic, UI,
  tests) with exactly one Mermaid sequence diagram of its riskiest flow. Use when
  asked how to read a PR, or how its pieces fit together.
argument-hint: "<pr>"
---

# PR story

A diff arrives in alphabetical order, which is almost never the order it makes sense
in. Re-order it so each file is read after what it depends on, and draw the one flow
that carries the most risk.

## Ground rules, shared by all six pr-* skills

- **Optional.** Nothing here gates a review or a merge; skipping this skill is always fine.
- **Sat acts alone.** Every next step you name is one the user (Sat) can take by
  themselves. On someone else's PR, work only from what already exists: the diff, the
  PR description, the linked ticket and git history. Never suggest asking the author.
- **Read-only, git and gh only.** No comments, reviews, labels, approvals, pushes,
  commits, checkouts or branch changes. No browser, database or running service, not
  even a read-only `SELECT`: no `psql`, no local Supabase or Docker stack. Read with
  `gh pr view|diff`, `gh issue view`, `gh api` GETs, `git fetch` (it adds objects and
  moves no local branch) and `git show|log|diff|grep|blame|ls-tree|merge-base`. Scratch
  files go under `/tmp`; pr-recall's card store is the only thing any pr-* skill writes.
- **Budgeted.** The budget is a ceiling, not a target: cut to fit. A line stays one
  line, never sub-bullets or a continuation. Each free-text field (a reason, question,
  claim, fact, correction) is at most 140 characters, in the text and in the JSON.
- **Pinned.** Resolve the head SHA once and compute everything against it. Open with
  the pin line `<owner>/<repo>#<n> @ <sha7>`, outside the budget.
- **Two outputs.** Plain text for Claude Code, then exactly one fenced `json` block with
  the same content, nothing extra, for the Lucidos Pulls app and review-prep rail to store.

## Budget

One diagram, plus the ordered file list at one line per step. Besides those, only the
"separate things" opener when it applies, and one line per extra flow.

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

## Step 1 — Order the files

Group every changed file into steps, so that each file comes after what it depends on.

- The default order is types → data → logic → UI → tests. Rename the layers to fit the
  repo: migrations → RPCs → store → screens → tests for a Supabase app, models →
  services → view models → views → tests for a Swift one.
- Config and CI go where they take effect. pr-lanes' Trust-class files (docs, QA specs,
  translations, fixtures, generated code, agent prompts that change no gate) go in a
  final `skip` step: docs are never a layer.
- At most 8 steps, not counting `skip`: merge the smallest adjacent ones to fit. A PR
  of Trust-class files only (docs, skills, slash commands) orders them in the steps.

Line: `<n>. <layer> — <files> — <what changes>`. Name at most 4 files per line by
basename, then `+N more`. Colliding basenames take the shortest unique tail of their
path: `en-US/translations.json`, `de-DE/translations.json`.

Done when every changed file sits in exactly one step: count them against `files` in
the metadata.

## Step 2 — Find the flows

A **flow** is one distinct behaviour change, traced from the entry point that runs it
(a screen action, an endpoint, a job, a CLI command, a webhook, a git or agent hook)
through the changed code. Walk each changed function's callers up (`git grep -n '<name>' "$SHA"`).

- Callers reaching the change only through one changed shared module (a hook, store,
  util, component) are one flow that starts at the module, not a flow per importer.
- Score a flow by its changed lines (added plus removed); a changed line scores once,
  in the flow it most directly serves. A refactor or speed-up with no behaviour change
  of its own is part of the flow it serves, never a flow of its own.
- Trust-class files are in no flow. Agent markdown (a skill, a slash command,
  `CLAUDE.md`) joins a flow only where it changes a gate, starting at what runs it.

Nothing that runs reaches changed code (docs or slash-command markdown only, config,
renames, dependency bumps): no flows, so skip Step 3 and output only the file list.

Group flows that share a changed file. With 3 or more groups, open the output (after
the pin) with `This PR does N separate things.`, N being the group count: each group
is a review of its own.

## Step 3 — Diagram the riskiest flow

Draw one flow as one ```` ```mermaid ```` `sequenceDiagram`. Exactly one diagram per run.

- Pick by risk, not size: the flow whose changed lines touch the most of pr-lanes'
  sensitive categories (`auth`, `money`, `data`, `security`, `concurrency`, `contract`,
  `gate`); changed lines break a tie.
- At most about 8 participants and 15 messages. If the flow is bigger, draw it at
  module level: participants become modules or services, messages the calls between them.
- Draw the changed hops, plus unchanged hops only where they connect two changed ones.
  End a new hop's text with ` [new]` and a changed hop's with ` [changed]`. Draw a hop
  the PR removes with `-x`, ending ` [removed]`.
- An unchanged entry point may open the diagram as context: end its participant label
  with ` [unchanged]`. Docs are never a participant.
- Participant ids are bare identifiers (`participant SS as StreakService`). Message
  text stays free of `;` and `#`, which break parsing, and of `file:line` citations.

Under the diagram, one line per other flow, at most 5, then `+N more flows`:
`Also: <entry> → <deepest changed hop> (<N> changed lines)`

## Output

Order: pin, the "separate things" opener if any, the diagram, the `Also:` lines, the steps.

````
pr-zone/przone-app#971 @ 3f9c2ab
```mermaid
sequenceDiagram
  participant FS as FreezeSheet [unchanged]
  participant ST as useStreakStore
  participant RPC as spend_freeze
  participant DB as streak_freezes
  FS->>ST: spendFreeze(day)
  ST->>RPC: rpc spend_freeze(day) [new]
  RPC->>DB: insert freeze row [new]
  ST-xDB: update the freeze count from the client [removed]
  RPC-->>ST: streak with frozen day [changed]
  ST-->>FS: re-render streak [changed]
```
Also: nightly streak_reset job → reset_streaks (12 changed lines)
1. data — 0042_streak_freezes.sql — adds streak_freezes and spend_freeze()
2. logic — useStreakStore.ts, streak.ts — spends a freeze through the RPC, keeps frozen days
3. UI — StreakCard.tsx — frozen-day badge
4. tests — streak.test.ts — frozen day keeps the streak
5. skip — database.types.ts, en.json — generated from the migration; badge copy
````

```json
{
  "schema": "pr-skills/story/v1",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "separate_things": null,
  "flows": [
    {"entry": "FreezeSheet: tap Use freeze", "kind": "screen", "changed_lines": 142, "diagrammed": true},
    {"entry": "nightly streak_reset job", "kind": "job", "changed_lines": 12, "diagrammed": false}
  ],
  "diagram": {"level": "function", "participants": 4, "messages": 6, "mermaid": "sequenceDiagram\n  participant FS as FreezeSheet [unchanged]\n  ..."},
  "steps": [
    {"n": 1, "layer": "data", "files": ["supabase/migrations/0042_streak_freezes.sql"], "what": "adds streak_freezes and spend_freeze()"},
    {"n": 2, "layer": "logic", "files": ["app/stores/useStreakStore.ts", "supabase/functions/streak.ts"], "what": "spends a freeze through the RPC, keeps frozen days"},
    {"n": 3, "layer": "UI", "files": ["app/streak/StreakCard.tsx"], "what": "frozen-day badge"},
    {"n": 4, "layer": "tests", "files": ["app/stores/streak.test.ts"], "what": "frozen day keeps the streak"},
    {"n": 5, "layer": "skip", "files": ["types/database.types.ts", "app/i18n/en.json"], "what": "generated from the migration; badge copy"}
  ]
}
```

`separate_things` is the group count when it is 3 or more, else `null`. `kind` is
`screen|endpoint|job|cli|webhook|other`; a flow starting at a shared module or a git
or agent hook is `other`. `level` is `function|module`. `diagram` is `null` when there are no
flows. The JSON `files` lists every path in full, unlike the text line.
