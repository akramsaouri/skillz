---
name: pr-understanding
description: >-
  Use when reviewing or understanding a pull request. Maps callers, tests, and
  blast radius (in parallel where possible), runs repo-aware standing checks
  (e.g. Supabase RPC row-level security, currency-unit consistency), and flags
  behavior-changing one-character edits. Handles visual-change, simple, and
  migration PRs.
license: MIT
---

# PR Understanding

> ⚠️ STUB — paste your real skill body below and delete this note.
> Reminder from your design notes: output an EPHEMERAL HTML page (don't commit
> an artifact), and use PARALLEL agents for gathering callers / tests /
> blast-radius.

## When to use
- Understanding an unfamiliar PR before review.
- Assessing blast radius / risk of a change.

## Procedure
1. TODO: paste your existing procedure here.

## Standing checks (highest-leverage part)
- Supabase RPC row-level security.
- Currency-unit consistency.
- Behavior-changing one-character edits (Step 6 flag).
- TODO: extend for visual-change PRs, simple PRs, migration PRs.
