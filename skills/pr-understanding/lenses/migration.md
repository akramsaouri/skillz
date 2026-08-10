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

1. **Reversibility.** Is there a down/rollback, and what does it restore? A down that
   recreates a dropped column recreates it *empty* — say so; a stub or
   `-- irreversible` means the change is one-way once it runs. That is a property of
   the migration the reader needs, whether or not it was deliberate.
2. **Destructive ops.** `DROP`, `TRUNCATE`, `ALTER … DROP`, `RENAME` (in-flight deploys
   still reading the old name stop finding it), type narrowing (`text`→`varchar(n)`),
   `NOT NULL` on an existing column without a default/backfill (fails on existing rows).
   Name each one and what it does to data that is already there.
3. **Locking / blocking.** Say which statements take a lock and what they block while
   they run — this is what the deploy actually does to prod, and the DSL hides it.
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
     authenticated client through an auto-generated API. If a function/RPC changed, say
     whether it checks the caller (`auth.uid()`) and whether it is `SECURITY DEFINER`
     (which **bypasses** RLS, so its own checks are the only ones that run).
   - **App-enforced (Rails, Django, Laravel, most Node/Go services):** the DB is open,
     so scoping lives in a default scope, base queryset, or middleware. Does the new
     table's model inherit it, or does it start unscoped? Whether the table carries a
     `tenant_id` column at all decides what scoping is available later — say which.
   - Either way: is the new column/table exposed by an auto-generated API, GraphQL
     schema, or admin panel that enumerates models (Django admin, ActiveAdmin)?
6. **Where it lands in the sequence.** Two PRs open at once each add a migration, and
   whichever merges second may still be ordered *before* the first on a fresh DB. Say
   where this one sits: its timestamp/number prefix against the newest on the base, the
   `dependencies` leaf it points at (Django), the `schema.rb`/`structure.sql` version it
   was generated from (Rails). Note whether it is written to be re-runnable
   (`IF NOT EXISTS`) — that decides what a partial failure leaves behind.
7. **Enum/constraint changes.** Adding an enum value is additive; **removing/renaming**
   one changes what existing rows using it mean. A new `CHECK` runs against data that is
   already there — say what it would reject.

## App-code sync (blast radius)

Where a schema change has no matching app change, the app is still speaking the old
shape — that is reach the patch does not show. Grep for:
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
(and new code against the old schema if the migration lags). Say which of the two
versions this schema can serve: only the new one, or both for a cycle. A `DROP`/`RENAME`
shipped in the same PR as its app change is the shape where that answer is "only the new
one" — the reader is the one who decides whether to split it expand→migrate→contract.

## Diagram

**`erDiagram` before → after** (two diagrams or one with the delta marked): tables,
the changed columns, and FK relationships. If it changes a write path, add a tiny
sequence diagram of app → RPC → table.

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
- "The non-null column at `file:line` is added in one statement — verify table X is
  small enough for that, or that you want the nullable→backfill→not-null split."
- "`database.types.ts` / `schema.rb` / the generated client was not regenerated in this
  PR — verify it doesn't need to be, and grep the old column name as a bare string for
  raw-SQL call sites the ORM rename never touched."
- "This migration's prefix is `<n>` — verify it still orders after whatever merged to
  the base while the PR was open."
