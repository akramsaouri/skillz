# Lens: Bugfix

Fires when the title/body says fix and the change is small and targeted on existing
logic. A bugfix map answers three things the diff alone doesn't: **(1) what the failing
behavior was, (2) what the fix changes in the mechanism, (3) what now exercises that
path.**

## Reconstruct the bug from the diff

- **What was the failing behavior?** State it from the diff + PR body. If the body
  doesn't say, say that — a fix whose bug is never described is a map with a hole in it,
  and it makes a good first verify item.
- **Where the fix sits relative to the cause.** Trace one level up: where did the bad
  value originate, and does the change touch that origin or the place the failure
  surfaced? A null-check at the crash site and a fix at the source are different changes
  with different reach — say which one this is, and let the reader draw the conclusion.
- **Reach of the fix.** Grep for the same pattern elsewhere. If three call sites share
  the shape and the diff changes one, the other two are blast-radius facts that never
  appear in the patch — name them at a `file:line`.

## The one-character trap (read the fix char by char)

Bugfixes concentrate behavior-flipping micro-edits — read each:

**Any language:** flipped boolean, changed default, off-by-one on a bound, `<`↔`<=`,
removed negation, reordered conditions (short-circuit changes), a `break`/`return`
moved in or out of a loop body, an early return added before a side effect.

**Language-specific one-character traps:**
- **JS/TS** — `||`→`??` (now `0`/`""`/`false` no longer fall through — often *is* the
  fix; say which values behave differently now); `==`↔`===`; added/removed `await`
  (changes the ordering, in either direction); `?.` swallowing a throw.
- **Python** — `is`↔`==` (identity vs equality — works for small ints, then doesn't);
  a mutable default arg; `except:` widened or narrowed; a missing `await` on a coroutine
  (silently never runs).
- **Go** — `=`↔`:=` (shadows the outer variable, so the fix writes to a copy); an `err`
  check added or dropped; `defer` moved relative to the error path; value↔pointer
  receiver (mutations stop propagating).
- **Swift/Kotlin** — `?`↔`!` force-unwrap, `??` default added, `let`↔`var`,
  `weak`/`strong` capture flipped, `==` vs `===` identity.
- **Java/C#** — `==` vs `.equals`/`Equals` on boxed values or strings.
- **SQL** — `WHERE` predicate on a nullable column (`!= 'x'` excludes `NULL` rows),
  `JOIN`↔`LEFT JOIN`, an added `DISTINCT` masking a duplicate-rows bug upstream.

## What now exercises the fixed path

Report the test surface as a fact, not a grade — whether the coverage is *enough* is the
reviewer's rail, not this one.

- **Which test touches the fixed path**, new or existing, at a `file:line`. If the diff
  adds none, the enumeration says that by itself.
- **Was a test added and then removed?** Check the commit list (Step 1), not the net
  diff — add-then-delete nets to zero and is invisible in `gh pr diff`. If it happened,
  quote the removing commit's message; that is the author's own reasoning, and it is
  rarely written down anywhere else.
- **If the body claims coverage, name the test it means** (hard rule 4, quote the claim)
  so the reader can check the claim against the file rather than take it on trust.

## Blast radius

Small, but: who else calls the changed function, and does any caller depend on the old
behavior? (Bugs get depended on.) Name them — the reader decides what it means.

## Diagram

Often none. If the bug is a **control-flow / ordering / state-machine** issue, a short
**`.rail`** of the buggy path against the fixed one is high-value — pair the steps so the
one that changed is the only row wearing `is-gone` / `is-new`, and the reader sees the
defect without being told where to look. For a **race or a mis-ordered call chain**, a
**`.ladder`** of the sequence; put the hop that fires too early — or the one whose error
went unhandled — in an `.lnote` beside it. Markup contract in Step 6.

## Verify these (bugfix)

- "The fix at `file:line` sits at the crash site; the bad value comes from `file:line`
  one level up — verify that's where you want it handled."
- "`||`→`??` at `file:line` — verify `0`/`""` was not a valid value that now behaves
  differently."
- "Verify a test at `file:line` fails on the pre-fix code — else the bug can silently
  return."
