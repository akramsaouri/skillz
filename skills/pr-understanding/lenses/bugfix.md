# Lens: Bugfix

Fires when the title/body says fix and the change is small and targeted on existing
logic. The reviewer's job is not "does this code run" but three sharper questions:
**(1) what was the root cause, (2) does this actually address it or just the symptom,
(3) is there a regression test so it stays fixed.**

## Reconstruct the bug from the diff

- **What was the failing behavior?** State it from the diff + PR body. If the body
  doesn't say, the fix is un-reviewable — make that the first verify item.
- **Root cause vs symptom.** Does the change fix the *cause* or paper over a *symptom*?
  A null-check added at the crash site when the real bug is upstream (why was it null?)
  is a symptom fix — it moves the crash, doesn't remove it. Trace one level up: where
  did the bad value originate?
- **Scope of the fix.** Is the same buggy pattern present elsewhere? A fix at one call
  site when three sites share the bug fixes 1/3. Grep for the pattern.

## The one-character trap (read the fix char by char)

Bugfixes concentrate behavior-flipping micro-edits — read each:

**Any language:** flipped boolean, changed default, off-by-one on a bound, `<`↔`<=`,
removed negation, reordered conditions (short-circuit changes), a `break`/`return`
moved in or out of a loop body, an early return added before a side effect.

**Language-specific one-character traps:**
- **JS/TS** — `||`→`??` (now `0`/`""`/`false` no longer fall through — often *is* the
  fix, or a *new* bug if `0` was a valid "unset"); `==`↔`===`; added/removed `await`
  (a race fix, or a new one); `?.` swallowing an error that should throw.
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

## Regression test — did it get locked in?

- Is there a **new/changed test** that **fails before, passes after**? A bugfix without
  a test will regress. If none, that's the top finding.
- Does the test assert the **root-cause behavior**, or just re-assert the happy path?

## Blast radius

Small, but: who else calls the changed function? Could the fix's behavior change break
a caller that *relied on* the old (buggy) behavior? (Bugs get depended on.)

## Diagram

Often none. If the bug is a **control-flow / ordering / state-machine** issue, a small
**before/after flowchart or stateDiagram** of the buggy vs fixed path is high-value —
it shows exactly which edge changed. For a race, a **sequenceDiagram** old vs new.

## Standing checks (bugfix)

- Root cause addressed, not just the symptom? (trace one level upstream)
- Same bug pattern absent elsewhere (grep)?
- Regression test added that fails-before / passes-after?
- No caller depended on the old (buggy) behavior?
- Any behavior-flipping micro-edit fully understood?

## Verify these (bugfix)

- "Fix at `file:line` — verify it addresses the root cause; where did the bad value
  originate (one level up)?"
- "`||`→`??` at `file:line` — verify `0`/`""` was not a valid value that now behaves
  differently."
- "Verify a test at `file:line` fails on the pre-fix code — else the bug can silently
  return."
