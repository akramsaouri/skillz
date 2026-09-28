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

At most 3 recall lines (or the no-match line), then one line per lane (or the no-lane
line). Nothing else.

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

## Step 1 — Recall

Run pr-recall's **Match** procedure (`<this-skill-dir>/../pr-recall/SKILL.md`, section
"Match") on this PR. Keep at most 3 hits, ordered `no` → `unclear` → `yes`. No store,
or no card overlaps: print `Recall: no matching cards` after the pin, the line Match
prints too, and emit `"recall": []`.

`✗ decision · #812 — Streak days are computed server-side — useStreak.ts:41 recomputes them on the client`

`✗` no, `?` unclear, `✓` yes.

## Step 2 — Signals

Read these from the metadata and the diff. They are also the JSON `signals`.

- **Trust-class files** fire no lane but remember (see its row); `ignored_files` counts
  them. Lockfiles, generated code, vendored deps, pure renames, formatting, version
  bumps, config with no app logic; docs and prose specs (markdown QA or design specs),
  whatever they change; translations, fixtures, snapshots; agent prompts, skills and
  hooks (`CLAUDE.md`, `.claude/`, `.agents/`) unless they change a gate: review, merge,
  auto-merge, release or a CI skip. A gate change is meaningful: it fires `behaviour`
  and is sensitive `gate`; as in pr-story, the file's other lines add no category.
- **Meaningful files** (`meaningful_files`): every other changed file. Only they fire
  the other lanes. Tests (`*.test.*`, `*.spec.*`, `__tests__/`, `tests/`) are
  meaningful, but no structure threshold counts them.
- **Areas**: of the meaningful files other than tests. An area is the first path
  segment, or the first two under `apps/`, `packages/`, `services/`, `libs/`, `src/`,
  `.claude/`, `.agents/`; a skill is its own area (`.claude/skills/release`). Root
  files are `(root)`, which counts for familiarity, never toward structure's ≥3.
- **New abstractions**: symbols exported at `$SHA` and not at `$BASE` (types,
  functions, classes, components, hooks), plus new tables, RPCs, endpoints and jobs.
  Not unexported helpers, a new file as such, re-exports, tests, or a moved symbol.
- **Author**: `own`, `other`, or `bot` (`dependabot`, `renovate`, a `[bot]` login).
- **Ticket**: a closing issue, or a tracker key (`PZ-88`, or a Sentry short ID such as
  `APP-40`) or issue URL in the title, body or `headRefName`, any case; else `null`.
- **Sensitive**: categories the meaningful lines alter, not just read, render or
  memoize; UI, copy and styling never count. `auth` (who may do what: sessions, tokens,
  roles, permissions, grants, RLS), `money` (payments, prices, entitlements; adding,
  removing or moving a paywall check, one that withholds a feature or opens the
  paywall, changes what a tier unlocks and counts; reading `isPro` only to choose what
  renders doesn't), `data` (deleting or migrating stored user or production data; QA
  fixtures, and seed or cleanup runs against a local test DB, don't count), `security`
  (what an attacker could reach: secrets, sandboxing, input validation; a line that is
  also `auth` is `auth` only), `concurrency` (races, locks, retries, ordering),
  `contract` (a breaking change to an export, API or schema that callers outside this
  diff use: a removed name, a changed signature or return shape, or a changed side
  effect such a caller's code observes or relies on: a write, a navigation, a throw, a
  returned value. Internal refresh mechanics, an added step that takes away nothing
  callers relied on, an effect re-homed so every caller still gets it, identical
  resulting state, additive changes and callers the diff updates don't count), `gate`
  (review, merge, release, CI skip, in code or prompts).
- **Familiarity**: how well Sat knew each area in the year before BASE's date (not
  today's: re-runs must agree). Count Sat's commits from `$BASE`, which leaves out this
  PR's own, one call per area with the area as one quoted word (`(root)` is
  `':(top,glob)*'`), and keep the lowest count with its area:
  `git log --since="$(git show -s --format=%cs "$BASE") 1 year ago" --author="$(git config user.email)" --format=%h "$BASE" -- 'widgets' | wc -l`

## Step 3 — Lanes

Test every lane against its trigger and tag each one that holds, in table order.

| Lane | Fires when | Next |
|---|---|---|
| intent | the PR adds a capability (a new route, screen, endpoint, job, flag or public API) or makes a capability, user-visible behaviour, gate or breaking contract change (by `contract`'s test), and its title and body never mention it: a new job the title names doesn't fire. Only a change of its own fires it, never a detail a reader of the body would expect (a singular "1 day remaining" in a countdown the body describes). Internals never count: PR templates often keep them out of the body. A fix or refactor alone is not intent | `/pr-intent` |
| structure | ≥3 areas besides `(root)`, ≥10 meaningful files besides tests, ≥3 new abstractions, or a move or refactor at scale | `/pr-story` |
| behaviour | a user can notice it (UI, copy, navigation, notifications, errors the user sees, public API or CLI output), including a sheet, toast or notification now shown a different number of times (a summary opening once per subscription change, not once per caller), or it changes a gate | `/pr-behaviour` |
| understanding | `sensitive` is not empty, or the least familiar area has ≤2 commits | `/pr-check` |
| remember | a recall hit reads `no`, the PR reverses a rule the repo writes down, or it writes down a new convention: a rule for code beyond its own lines, in `CLAUDE.md`, docs or a comment ("mount only from the bridge"), which fires this even in a Trust-class file. A comment explaining its own lines, or a decision that lives only in code, does not | `/pr-recall create` once merged |
| trust | there are no meaningful files: every change is Trust-class | none |

- **trust is exclusive.** No meaningful files: print the trust line and no other lane
  but remember. Any meaningful file: trust never fires.
- No lane holds: print `No lane: nothing here needs another pr-* skill.`
- On Sat's own PR, the intent line's next step is `/pr-intent <n> "<your why>"`.
- A reason names evidence Sat can check: "adds `POST /streaks/freeze` (api/streaks.ts)
  for ticket PZ-88", not "adds a feature". An understanding reason names the trigger
  that held: the category, or the area and its count.

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
with no meaningful files. **v2**: v1's `sensitive` held `ui|schema|money|auth`, and
its `familiarity` was a bare number.
