---
name: pr-behaviour
description: >
  List what a pull request changes for its users as at most 5 before → after
  lines, each UI change shown in a simulator screenshot or a mockup drawn from
  the diff. Use when asked what users will notice, or what a PR looks like.
argument-hint: "<pr> [--out-dir <abs-dir>] [--path-prefix <prefix>]"
---

# PR behaviour

What the PR does to the person using the product, not to the code. Every change is a
difference between two states you have read: the before-state at the merge base and
the after-state at the head.

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

At most 5 changes, one line each, and at most 2 shots per change (one `after`, and a
`before` where it helps).

## Acquire

Input: a PR number in the current repo, `owner/repo#n`, or a PR URL. Pass it to
`gh pr` as `-R <owner/repo> <n>`: gh reads `owner/repo#n` as a branch name. For a
bare number, `<owner/repo>` is `gh repo view --json nameWithOwner -q .nameWithOwner`.

```bash
mktemp -d /tmp/pr-<n>.XXXXXX   # prints <T>: one dir per run
gh pr view -R <owner/repo> <n> --json number,url,title,body,author,state,mergedAt,headRefName,headRefOid,baseRefOid,baseRefName,files,additions,deletions,closingIssuesReferences > <T>/pr.json
jq -r '.headRefOid, .baseRefOid, .baseRefName' <T>/pr.json   # prints <sha>, <base-oid>, <base-ref>; resolve ONCE: FETCH_HEAD is overwritten by any later fetch
gh pr diff -R <owner/repo> <n> > <T>/pr.diff   # the net diff; --patch is a per-commit series that repeats files
git fetch origin refs/pull/<n>/head <base-ref>
git merge-base <base-oid> <sha>   # prints <base>: the before-state
git show <sha>:<path>; git grep -n '<symbol>' <sha>   # read the head without checking it out
date -u +%Y-%m-%dT%H:%M:%SZ   # prints <now>: the JSON generated_at; run it last, just before writing the JSON
```

- **Shot files.** `--out-dir <dir>` is the absolute directory the shot images go in;
  `--path-prefix <prefix>` is what each shot's JSON `path` starts with, e.g.
  `artifacts/review-cockpit/shots/przone-1090-582c9b1`. With neither, the out-dir is
  `./.pr-shots/<slug>-<n>-<sha7>` and the prefix `.pr-shots/<slug>-<n>-<sha7>`, where
  `<slug>` is the repo's name part (`przone-app`). With only `--out-dir`, the prefix is the out-dir as given. A
  `--path-prefix` without `--out-dir` is an error: stop and say so. Create the dir
  with `mkdir -p <out-dir>`.

- **Literals only.** No `$(...)`, backticks or variables: they die between tool calls, and
  a permission guard refuses substitution. Run each command alone, read its output, and
  paste the value into the next command as a literal (`<T>`, `<sha>`, `<base>` above).
- `repo` in the JSON is `owner/name`, taken from the PR URL.
- **Own PR**: `author.login` equals `gh api user -q .login`.
- **Not cloned locally** (or `origin` is another repo): read files with
  `gh api "repos/<owner/repo>/contents/<path>?ref=<sha>" -H 'Accept: application/vnd.github.raw'`
  and history with `gh api "repos/<owner/repo>/commits?path=<path>"`.

## Step 1 — Find the user-visible changes

A change is user-visible when someone using the product, or calling its public API or
CLI, could notice it: layout, copy, states (loading, empty, error), navigation and what
is reachable from where, notifications and emails, timing, permissions, the data shown
(formatting, rounding, sort order), public API responses, CLI output. Refactors,
logging and tests are internal.

For each candidate, read both sides: `git show <base>:<path>` and `git show <sha>:<path>`.
A `+` line alone shows the after-state, not the change.

Line: `<surface>: <before> → <after> (<file:line>)`, e.g.
`Settings › Units: toggle lived under Profile → moved to the Settings root (SettingsScreen.tsx:84)`

More than 5: keep the ones that reach the most users, and put the omitted count in
`more`. None: print `No user-visible change.`

Done when every changed UI, copy, API and CLI file was read at both `<base>` and `<sha>`.

## Step 2 — Show every UI change

A UI change must be seen, not only read. **Every change on a UI surface carries at
least one shot**: a screen, sheet, modal, card, toast, notification, email or web page
whose look, copy, layout or states change. Never ship such a change with `shots: []`.

- **Capture tool.** If the repo carries capture tooling (Maestro flows, Playwright
  screenshots, fastlane snapshot, a `*screenshot*` script), name its path in
  `capture_tool`, else `null`.
- **Kind.** A shot is `sim`, a real simulator or browser screenshot, only when
  `capture_tool` is set and a simulator or browser already runs the build at `<sha>`
  that this run can drive with that tool. Never build, install, check out or start a
  stack to get there. Otherwise it is `mockup`. A mockup is a full answer, not a
  fallback to apologise for: never wait on, or skip a change for, the simulator.
- **State.** Pick the state that shows the change, and write it in the shot's `state`:
  where the surface is and the data it needs, e.g.
  `Home tab, signed in, 5-day streak, one freeze held, yesterday missed`.
- **Mockup.** Draw the `after` state from the diff at `<sha>`: the component's
  structure and order, its copy verbatim from the code or the strings file, its
  colours, sizes and icons from the theme or style values it reads. Draw only the
  surface and enough context to place it; a part you cannot read from the code is a
  grey box with a plain label, never invented detail. Write a self-contained SVG (no
  external fonts, images or scripts; 390 wide for a phone screen) with the Write tool,
  or HTML rendered to PNG when a headless renderer is already installed. Every mockup
  carries a visible top banner `MOCKUP — drawn from the diff, not a screenshot`.
  Images in the PR description are a reference for the look, never a shot.
- **Before.** Add a `before` shot, drawn the same way from `<base>`, when the change
  alters something already on screen (moved, restyled, recopied, removed) and the pair
  shows it better than the after alone. A brand-new surface gets only `after`.
- **Not a UI change.** A change with no surface of its own (a catalog or DB change, an
  API response, CLI output, timing) gets a mockup of the screen where its effect shows,
  when one does, else `shots: []` and a `no_shot_reason` of at most 140 characters.
- **Files.** Write each image to `<out-dir>/<i>-<side>.<svg|png>`, where `<i>` is the
  change's 1-based place in `changes` and `<side>` is `after` or `before`; its `path`
  is `<path-prefix>/<i>-<side>.<svg|png>`. Check each SVG parses with
  `xmllint --noout <file>` and fix it until it does.
- Writing to `<out-dir>`, `mkdir -p` on it, `xmllint`, a headless renderer on a local
  HTML file, and driving `capture_tool` against an already-running build are the only
  exceptions to the Read-only rule.

Done when every change on a UI surface has a shot whose file exists at its path.

## Output

Each change line ends with its shots, `[<kind> <side>: <path>]`, or
`[no shot: <no_shot_reason>]`.

```
pr-zone/przone-app#971 @ 3f9c2ab
Streak card: no badge → frozen days show a snowflake badge (StreakCard.tsx:31) [mockup after: .pr-shots/przone-app-971-3f9c2ab/1-after.svg] [mockup before: .pr-shots/przone-app-971-3f9c2ab/1-before.svg]
Settings › Units: toggle lived under Profile → moved to the Settings root (SettingsScreen.tsx:84) [mockup after: .pr-shots/przone-app-971-3f9c2ab/2-after.svg]
Streak reminder: pushed at 20:00 UTC → at 20:00 in the user's time zone (reminders.ts:22) [no shot: timing only; the push text and look are unchanged]
```

```json
{
  "schema": "pr-skills/behaviour/v2",
  "pr": {"repo": "pr-zone/przone-app", "number": 971, "url": "https://github.com/pr-zone/przone-app/pull/971", "head_sha": "<40-hex>"},
  "generated_at": "2026-09-27T09:14:00Z",
  "changes": [
    {"surface": "Streak card", "before": "no badge", "after": "frozen days show a snowflake badge", "evidence": "app/streak/StreakCard.tsx:31",
     "shots": [
       {"kind": "mockup", "side": "after", "path": ".pr-shots/przone-app-971-3f9c2ab/1-after.svg", "caption": "Streak card with a snowflake badge on the frozen day", "state": "Home tab, signed in, 5-day streak, one freeze held, yesterday missed"},
       {"kind": "mockup", "side": "before", "path": ".pr-shots/przone-app-971-3f9c2ab/1-before.svg", "caption": "Streak card before: the missed day shows as a gap", "state": "Home tab, signed in, 5-day streak, yesterday missed"}
     ],
     "no_shot_reason": null},
    {"surface": "Settings › Units", "before": "toggle lived under Profile", "after": "moved to the Settings root", "evidence": "app/settings/SettingsScreen.tsx:84",
     "shots": [
       {"kind": "mockup", "side": "after", "path": ".pr-shots/przone-app-971-3f9c2ab/2-after.svg", "caption": "Settings root with the Units toggle under General", "state": "Settings tab, signed in, metric units"}
     ],
     "no_shot_reason": null},
    {"surface": "Streak reminder", "before": "pushed at 20:00 UTC", "after": "at 20:00 in the user's time zone", "evidence": "supabase/functions/reminders.ts:22",
     "shots": [], "no_shot_reason": "timing only; the push text and look are unchanged"}
  ],
  "more": 0,
  "capture_tool": ".maestro/"
}
```

`generated_at` is `<now>`, printed by Acquire's `date` line and pasted as a literal.
`shots` is always an array, `[]` only beside a `no_shot_reason`; `no_shot_reason` is
`null` whenever `shots` has one. A shot's `kind` is `sim|mockup`, `side` is
`after|before` (the `after` first), `caption` says what the image shows in at most 140
characters, and `state` is the capture state it shows. `capture_tool` is `null` when
the repo has none. With no user-visible change, `changes` is `[]`.
**v2**: `shots` changes from a `{before, after, source}` object or `null` to an array
of shot objects, every UI change carries one, and `no_shot_reason` is new. The
top-level `capture` list and the `--shots` input are gone: each `capture` entry's
`where` and `state` live on in its shot's `state`.
