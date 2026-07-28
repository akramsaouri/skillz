# Lens: Refactor / no-behavior-change

Fires on renames, moves, de-exports, extractions, type-only edits — where the author
**claims no behavior change**. The entire value of this lens is **proving that claim,
or catching where it's false.** A "pure refactor" that quietly changes behavior is the
most dangerous PR shape, because reviewers relax exactly when they shouldn't.

## Strategy: shrink the diff to the part that isn't noise

1. **Run difftastic** (see README) if available — a structural/AST diff makes renames,
   reindents, and moved blocks stop reading as changes, leaving only the *real* delta.
   `GIT_EXTERNAL_DIFF=difft git diff <base>...<head>`.
2. **Separate mechanical from semantic.** Mechanical: rename, move file, reindent,
   extract-with-identical-body, import reorder. Semantic: any change to a value, a
   condition, an order of operations, a default, a signature, a visibility. **Only the
   semantic part can change behavior — that's what you read.**

## Where "pure" refactors leak behavior — check each

- **Extracted function drops a closure variable** or captures a different one.
- **`export` removed** (de-export): grep for external importers — did they all move,
  or is something now unresolved? (This is the classic — an unused-looking export was
  used by a test or another module.)
- **Default param / default export** changed during the move.
- **Order of side effects** changed when code was reordered (logging, mutation, async
  sequencing).
- **`==` vs `===`, `||` vs `??`** "cleaned up" during the refactor — behavior flip.
- **Type widening/narrowing** that changes what values are accepted at runtime (if the
  type is enforced anywhere, e.g. a validator/zod schema).
- **Memoization / referential identity** changed (new object literal each render).

## Blast radius

For every moved/renamed/de-exported symbol: **every import site updated?** Grep the
old name/path across the repo — a stale import is a build break the diff hides. Tests
that imported the old path?

## Diagram

Usually **none** (nothing flows differently). If the refactor reorganizes module
boundaries, a small **before/after module graph** (flowchart) showing what now imports
what earns its place. Otherwise skip.

## Standing checks (refactor)

- Every moved/renamed/de-exported symbol's import sites updated? (grep old name → 0 hits)
- No `==`/`===`, `||`/`??`, default, or condition changed under cover of the move?
- Extracted functions capture the same variables and run side effects in the same order?
- Public API surface identical (or the change is called out, not silent)?
- Tests still import valid paths and still exercise the moved code?

## Verify these (refactor)

- "Author claims no behavior change — the only *semantic* lines after difftastic are
  `file:line`; verify each preserves the old behavior exactly."
- "`export` removed from `X` at `file:line` — verify no remaining importer (grep) is
  now broken."
- "Function extracted at `file:line` — verify it captures the same closure vars and
  the call order of side effects is unchanged."
