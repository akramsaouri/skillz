# Lens: Migration / schema

Fires on `*.sql` and any migration toolchain: `**/migrations/**`, `supabase/migrations`,
Prisma/Drizzle/TypeORM schema, Rails `db/migrate` + `schema.rb`, Django `migrations/`,
Alembic `versions/`, Flyway/Liquibase, `golang-migrate`, Ecto `priv/repo/migrations`.
**Highest-stakes lens** — a bad migration corrupts data or takes a lock that stalls
prod. Treat migrations as **Deep lane** even if the file count is small. The migration
file is load-bearing; read it line by line.

**Read the generated SQL, not just the DSL.** An ORM migration (`add_column`,
`AlterField`, a Prisma schema edit) hides the DDL that actually runs — and the DDL is
where the lock is. If the PR doesn't include the SQL, say which statement you're
inferring and make it a verify item.

## Read the DDL for these, in order

1. **Reversibility.** Is there a down/rollback? Does the down actually **reverse** the
   up (drop what was added, restore what was dropped/renamed), or is it a stub /
   `-- irreversible`? A `DROP COLUMN` with no down is data loss on rollback — flag it.
2. **Destructive ops.** `DROP`, `TRUNCATE`, `ALTER … DROP`, `RENAME` (renames break
   in-flight deploys reading the old name), type narrowing (`text`→`varchar(n)`),
   `NOT NULL` on an existing column without a default/backfill.
3. **Locking / blocking.** On a big table these stall prod — flag each with the safe
   alternative.
   - **Postgres:** `ALTER TABLE … ADD COLUMN … DEFAULT` (rewrites the table pre-PG11),
     `CREATE INDEX` **without `CONCURRENTLY`** (locks writes), `ALTER … SET NOT NULL`
     (full scan — prefer a `NOT VALID` check constraint then `VALIDATE`),
     `ADD CONSTRAINT … FK` without `NOT VALID`. Also: no `lock_timeout`, so a blocked
     `ALTER` queues every subsequent read behind it.
   - **MySQL:** is the op `ALGORITHM=INPLACE`/`INSTANT`, or does it copy the table?
     Pre-8.0 an `ADD COLUMN` rewrites; changing a column type almost always does.
     Is `pt-online-schema-change`/`gh-ost` expected here and skipped?
   - **SQLite** (mobile/Expo, Core Data, Room): there's no real `ALTER` — most changes
     become create-copy-drop-rename. On-device that runs on the **user's** data with no
     rollback; check the app handles a failed upgrade without wiping the DB.
4. **Backfill ordering.** New non-null column: is it added nullable → backfilled →
   set not-null in separate steps, or all at once (locks + fails on existing rows)?
   Is the backfill in the same txn as a lock-heavy DDL?
5. **Tenancy — where is access actually enforced for this new table?** Every new table
   holding user data needs an answer, and it differs by stack. Name the layer and cite it.
   - **DB-enforced (Postgres RLS — Supabase, Hasura, PostgREST, RDS):** is
     `ENABLE ROW LEVEL SECURITY` present *and* are policies defined? Enabling RLS with
     no policy denies all; a new table with **no RLS at all** is readable by any
     authenticated client through an auto-generated API. If a function/RPC changed, does
     it still check the caller (`auth.uid()`), and is it `SECURITY DEFINER` (which
     **bypasses** RLS — the sharpest edge here)?
   - **App-enforced (Rails, Django, Laravel, most Node/Go services):** the DB is open,
     so scoping lives in a default scope, base queryset, or middleware. Does the new
     table's model inherit it, or does it start unscoped? A missing `tenant_id` on the
     table makes correct scoping impossible later.
   - Either way: is the new column/table exposed by an auto-generated API, GraphQL
     schema, or admin panel that enumerates models (Django admin, ActiveAdmin)?
6. **Ordering / collisions.** Two PRs open at once each add a migration; whichever
   merges second may be ordered *before* the first on a fresh DB. Check the migrations
   dir for a **duplicate or out-of-order timestamp/number prefix**, a Django migration
   whose `dependencies` point at a now-superseded leaf (two leaf nodes = broken graph),
   or a Rails `schema.rb`/`structure.sql` whose version doesn't match the newest
   migration. And is the migration **idempotent** (`IF NOT EXISTS`) where a partial
   failure means it re-runs?
7. **Enum/constraint changes.** Adding an enum value is fine; **removing/renaming** one
   breaks rows using it. `CHECK` constraints validated against existing data?

## App-code sync (blast radius)

A schema change with no matching app change is a red flag. Grep for:
- Every read/write of the changed table/column in app code, **plus the checked-in
  artifact that mirrors the schema** — is it regenerated in this PR? By stack:
  `database.types.ts` (Supabase), `schema.prisma` + Prisma client, `schema.rb` /
  `structure.sql` (Rails), `models.py` (Django), sqlc/jOOQ/Ent output, GraphQL SDL.
  A stale artifact means CI passes locally and prod diverges.
- API/RPC/serializer shapes that expose the column.
- **Raw SQL and string-built queries** — an ORM rename won't touch them, so grep the
  old column name as a bare string across the repo (including tests and fixtures).
List any use site the diff did NOT update.

**Deploy ordering.** Old app code runs against the new schema during a rolling deploy
(and new code against the old schema if the migration lags). Is this change
**backward-compatible for one deploy cycle**, or does it require expand→migrate→contract
across two PRs? A `DROP`/`RENAME` shipped with its app change in one PR is the common
break.

## Diagram

**`erDiagram` before → after** (two diagrams or one with the delta marked): tables,
the changed columns, and FK relationships. If it changes a write path, add a tiny
sequence diagram of app → RPC → table.

## Standing checks (migration)

- Down-migration reverses the up? (`file:line`)
- No table-rewrite or non-concurrent index build locking a large table?
- Tenancy enforced for the new table — DB policy or app-level scope, named and cited?
- Non-null column added via nullable→backfill→not-null, not in one locking step?
- Schema-mirroring artifact (types/`schema.rb`/client) regenerated, and raw-SQL call
  sites updated?
- Backward-compatible for one rolling-deploy cycle, or split expand→contract?
- Migration prefix/dependency graph does not collide with another open migration?

## Verify these (migration)

- "Does the down-migration at `file:line` actually restore the dropped column's data,
  or just recreate an empty column?"
- "`CREATE INDEX` at `file:line` — is it `CONCURRENTLY`? On table X's row count, the
  plain form locks writes for the duration."
- "New table `T` — verify tenancy is enforced somewhere and say where: a DB policy at
  `file:line`, or the app-level scope every query inherits. If neither, any
  authenticated caller can read every row."
- "`DROP`/`RENAME` at `file:line` ships with its app change — verify old pods running
  mid-deploy don't still read the old name."
