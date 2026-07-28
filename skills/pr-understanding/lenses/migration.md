# Lens: Migration / schema

Fires on `*.sql`, `**/migrations/**`, `supabase/migrations`, Prisma/Drizzle/TypeORM
schema, any DDL. **Highest-stakes lens** — a bad migration corrupts data or takes a
lock that stalls prod. Treat migrations as **Deep lane** even if the file count is
small. The migration file is load-bearing; read it line by line.

## Read the DDL for these, in order

1. **Reversibility.** Is there a down/rollback? Does the down actually **reverse** the
   up (drop what was added, restore what was dropped/renamed), or is it a stub /
   `-- irreversible`? A `DROP COLUMN` with no down is data loss on rollback — flag it.
2. **Destructive ops.** `DROP`, `TRUNCATE`, `ALTER … DROP`, `RENAME` (renames break
   in-flight deploys reading the old name), type narrowing (`text`→`varchar(n)`),
   `NOT NULL` on an existing column without a default/backfill.
3. **Locking / blocking.** On Postgres: `ALTER TABLE … ADD COLUMN … DEFAULT`
   (rewrites the table pre-PG11), `CREATE INDEX` **without `CONCURRENTLY`** (locks
   writes), `ALTER … SET NOT NULL` (full scan), `ADD CONSTRAINT … FK` without `NOT
   VALID`. On a big table these take a lock that stalls prod. Flag each with the safe
   alternative.
4. **Backfill ordering.** New non-null column: is it added nullable → backfilled →
   set not-null in separate steps, or all at once (locks + fails on existing rows)?
   Is the backfill in the same txn as a lock-heavy DDL?
5. **RLS (Supabase/Postgres).** If a table is created or columns added: is
   `ENABLE ROW LEVEL SECURITY` present and are policies defined? A new table without
   RLS is world-readable through PostgREST. If an RPC/function changed, does it still
   enforce the auth check (`auth.uid()`)? **This is the #1 Supabase footgun.**
6. **Idempotency / collisions.** `IF NOT EXISTS` where a re-run is possible? Does the
   migration **timestamp/number collide** with another open PR's migration (a known
   past bug — check the migrations dir for duplicate prefixes)?
7. **Enum/constraint changes.** Adding an enum value is fine; **removing/renaming** one
   breaks rows using it. `CHECK` constraints validated against existing data?

## App-code sync (blast radius)

A schema change with no matching app change is a red flag. Grep for:
- Every read/write of the changed table/column in app code + generated types
  (`database.types.ts`, ORM models) — are they regenerated in this PR?
- API/RPC shapes that expose the column.
List any use site the diff did NOT update.

## Diagram

**`erDiagram` before → after** (two diagrams or one with the delta marked): tables,
the changed columns, and FK relationships. If it changes a write path, add a tiny
sequence diagram of app → RPC → table.

## Standing checks (migration)

- Down-migration reverses the up? (`file:line`)
- No un-`CONCURRENTLY` index / table-rewrite lock on a large table?
- New table/columns have RLS enabled + policies? Changed RPC keeps `auth.uid()`?
- Non-null column added via nullable→backfill→not-null, not in one locking step?
- Generated types + app call sites updated to match?
- Migration prefix does not collide with another migration in the dir?

## Verify these (migration)

- "Does the down-migration at `file:line` actually restore the dropped column's data,
  or just recreate an empty column?"
- "`CREATE INDEX` at `file:line` — is it `CONCURRENTLY`? On table X's row count, the
  plain form locks writes for the duration."
- "New table `T` — verify RLS is enabled and a policy exists (`file:line`), else it's
  readable by any authenticated client via PostgREST."
