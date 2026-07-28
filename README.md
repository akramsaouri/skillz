# skillz

Sat's personal [Claude Code](https://claude.com/claude-code) skills, packaged so
anyone can install them — the same way you install skills from `skills.sh`.

This one repo works **two** ways:

1. **skills.sh / `npx skills`** — reads `skills/*/SKILL.md` (Route A).
2. **Claude Code native plugin marketplace** — reads `.claude-plugin/` (Route B).

Both point at the *same* `skills/` directory, so there's nothing to keep in sync.

---

## Install (for other people)

### Route A — skills.sh (no marketplace needed)
```bash
npx skills add akramsaouri/skillz
```
Installs every skill under `skills/`. Works the moment the repo is public.
(To show up in `npx skills find`, submit the repo once at skills.sh — until then
it's install-by-URL only.)

### Route B — Claude Code native plugin
```
/plugin marketplace add akramsaouri/skillz
/plugin install sat-skills@skillz
```
Native to Claude Code — gives versioning and `/plugin update`.

---

## Layout
```
skillz/
├── .claude-plugin/
│   ├── marketplace.json   # catalog Claude Code reads (Route B)
│   └── plugin.json        # this repo IS one plugin (source ".")
├── skills/                # source of truth — read by BOTH routes
│   ├── _TEMPLATE/SKILL.md # copy this to start a new skill
│   └── pr-understanding/SKILL.md
├── LICENSE
└── README.md
```

## Add a new skill
1. `cp -r skills/_TEMPLATE skills/<my-skill>`
2. Edit `skills/<my-skill>/SKILL.md` — set `name` + a sharp `description`
   (the `description` is the trigger Claude matches on: write it as *"Use when …"*).
3. Drop any helper scripts/templates alongside it and reference them by relative path.
4. Commit + push. Done — both install routes pick it up automatically.

## Before you publish repo-aware skills
Some of my local skills (qa-author, qa-nightly, run-przone) assume the
`pr-zone/przone-app` repo, Supabase RPCs, a specific driver script, etc.
**Genericize them or document the assumptions** before adding them here, or
they'll misfire in someone else's repo.

## Want granular installs later?
Split into multiple plugins: make `plugins/<name>/` dirs, each with its own
`.claude-plugin/plugin.json` + `skills/`, and list each in `marketplace.json`
with `"source": "./plugins/<name>"`. Then people can install just one bundle.
