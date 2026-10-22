# skillz

## Installation

### Claude Code (auto-updates)

```
/plugin marketplace add akramsaouri/skillz
/plugin install akramsaouri-skillz@akramsaouri-skillz
```

### Codex, Cursor, and other agents

```bash
npx skills@latest add akramsaouri/skillz
```

_Re-run it to pull my later changes._

## Skills

### PR review suite

Six small skills for understanding a pull request. Each one is optional, strictly
read-only toward GitHub, and runs on its own as a slash command. Each ends its output
with one JSON block that the Lucidos Pulls app and review-prep rail read. pr-story
needs Node 20+: its first run installs the pinned `pele` into the skill's directory.

| Skill | What it does | Budget |
|---|---|---|
| **[pr-lanes](./skills/pr-lanes/SKILL.md)** | First pass and router: tags the PR with lanes (intent, structure, behaviour, understanding, remember, trust), names the skill to run next, and surfaces past decisions the PR touches | 1 line per lane + ≤3 recall hits |
| **[pr-intent](./skills/pr-intent/SKILL.md)** | On your PR, challenges the why you wrote against the diff. On someone else's, drafts a why with every guess tagged `[guess]` | 3 sentences + ≤5 mismatches |
| **[pr-story](./skills/pr-story/SKILL.md)** | Reading order for the diff, plus one diagram for each of its biggest flows (up to 3), each a sequence, state or flowchart diagram depending on the change, checked with [Pele](https://pele.run) before it ships | ≤3 diagrams + 1 line per step |
| **[pr-behaviour](./skills/pr-behaviour/SKILL.md)** | What changes for users, before → after, with a simulator screenshot or a mockup drawn from the diff for every UI change | ≤5 changes |
| **[pr-check](./skills/pr-check/SKILL.md)** | Tests your understanding: a consequence quiz with grading, teach-back corrections, or a drill (Socratic back-and-forth) | 3 questions, ≤5 corrections |
| **[pr-recall](./skills/pr-recall/SKILL.md)** | Keeps one-line cards on how merged code works, and flags an open PR that undoes one | ≤3 cards per PR |

Start with `/pr-lanes 971` and run what it points to, e.g. `/pr-check 971 --depth quiz`.
