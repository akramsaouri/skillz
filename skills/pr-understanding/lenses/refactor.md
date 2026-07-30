# Lens: Refactor / no-behavior-change

Fires on renames, moves, de-exports, extractions, type-only edits — where the author
**claims no behavior change**. The entire value of this lens is **proving that claim,
or catching where it's false.** A "pure refactor" that quietly changes behavior is the
most dangerous PR shape, because reviewers relax exactly when they shouldn't.

## Strategy: shrink the diff to the part that isn't noise

1. **Run difftastic if it's already installed** (`command -v difft`) — a structural/AST
   diff makes renames, reindents, and moved blocks stop reading as changes, leaving only
   the *real* delta: `GIT_EXTERNAL_DIFF=difft git diff <base>...<head>`.
   **Do not install it for the user.** Without it, get most of the way there with
   `git diff -M -C -w <base>...<head>` (`-M`/`-C` detect renames and copies, `-w`
   ignores whitespace) — then `--stat` to spot files whose churn is pure formatting.
2. **Separate mechanical from semantic.** Mechanical: rename, move file, reindent,
   extract-with-identical-body, import reorder. Semantic: any change to a value, a
   condition, an order of operations, a default, a signature, a visibility. **Only the
   semantic part can change behavior — that's what you read.**

## Where "pure" refactors leak behavior — check each

- **Extracted function drops a closure variable** or captures a different one — or in
  Go/Java, captures a **loop variable** whose binding differs from the original.
- **Visibility narrowed**: `export` removed (JS/TS), an identifier lowercased (Go),
  `pub` dropped (Rust), `private`/`internal` added (Swift/Kotlin/Java/C#), `__all__`
  trimmed (Python). Grep for external importers — did they all move, or is something now
  unresolved? (This is the classic — an unused-looking export was used by a test.)
- **Default argument / default export** changed during the move. In Python, watch a
  **mutable default** (`def f(x=[])`) introduced by an extraction.
- **Order of side effects** changed when code was reordered (logging, mutation, async
  sequencing, transaction boundaries).
- **Equality / nullish operators "cleaned up"** — a behavior flip in any language:
  `==`→`===` and `||`→`??` (JS/TS), `==`→`is` (Python), `==`→`equals` (Java/Kotlin),
  `==`→`===` (Swift identity vs equality).
- **Type widening/narrowing** that changes what's accepted at *runtime* — only matters
  where the type is actually enforced (zod/pydantic/serde validator, not a stripped
  TS annotation).
- **Identity / caching semantics** changed: a new object literal each React render
  (breaks memo), a struct→class switch (value→reference in Swift/C#), a changed
  `hashCode`/`__eq__`, or a lost `@lru_cache`/`useMemo`.

## Blast radius

For every moved/renamed/de-exported symbol: **every import site updated?** Grep the
old name/path across the repo — a stale import is a build break the diff hides. Tests
that imported the old path?

## Diagram

Usually **none** (nothing flows differently). If the refactor reorganizes module
boundaries, a small **before/after module graph** (flowchart) showing what now imports
what earns its place. Otherwise skip.

## Standing checks (refactor)

- Every moved/renamed/visibility-narrowed symbol's import sites updated? (grep old
  name → 0 hits, including tests, string-based DI, and reflection/dynamic lookups)
- No equality/nullish operator, default argument, or condition changed under the move?
- Extracted functions capture the same variables and run side effects in the same order?
- Public API surface identical (or the change is called out, not silent)?
- Tests still import valid paths and still exercise the moved code?

## Verify these (refactor)

- "Author claims no behavior change — the only *semantic* lines after the structural
  diff are `file:line`; verify each preserves the old behavior exactly."
- "`X` at `file:line` is no longer publicly visible — verify no remaining importer
  (grep) is now broken."
- "Function extracted at `file:line` — verify it captures the same closure vars and
  the call order of side effects is unchanged."
