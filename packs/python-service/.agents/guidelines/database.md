# Database guidelines for services

The database outlives every version of the code. Treat changes to it as the riskiest part of a release. Where `.agents/project.md` or the project's migrations settle a convention differently, follow them.

## Migrations

- Every schema change is a migration in the repository, reviewed like code and applied by the deploy, never by hand.
- A migration must work while the previous version of the service is still running. Split breaking changes into steps across releases, for example: add the new column, write to both, backfill, switch reads, then drop the old column. Say in the pull request which release each step ships in.
- Never edit a migration that has run anywhere shared; write a new one.
- Set a lock timeout before statements that take strong locks (on PostgreSQL, `SET LOCAL lock_timeout` inside the migration's transaction, so it does not leak to other work on a pooled connection). A migration that times out on a busy table fails and is retried later, instead of blocking every query queued behind it.
- Build indexes on large tables without blocking writes (`CREATE INDEX CONCURRENTLY` on PostgreSQL). Such statements cannot run inside a transaction: give them a migration of their own that the migration tool runs outside one (for example Alembic's `autocommit_block()`, or `atomic = False` in Django). If the build fails, drop the invalid index it leaves behind before you retry: `IF NOT EXISTS` would skip it, and the index would never be built.
- Large backfills run in batches, each in its own short transaction, outside the migration that changes the schema.
- Make migrations reversible where you can. When one is not, say so in the pull request, and run it first on data of production size.
- Where migrations run by hand or the tool does not track what has run, make them safe to re-run (`IF NOT EXISTS`, `IF EXISTS`); elsewhere, let a migration fail when the schema is not what it expects.

## Queries and transactions

- Use bound parameters for every value; never build SQL by formatting strings. Quote identifiers you cannot avoid putting in SQL.
- Keep transactions short: validate input before you open one, and never wait on the network inside one.
- Do not open a transaction inside code that already runs in one unless the project's database layer supports nesting explicitly.
- Watch for N+1 queries: load related data in one query or a batch.
- Every query on a large table uses an index. Read the plan of every new query against realistic data, and read it again before you add an index for it.
- Paginate by key (`WHERE id > :last ORDER BY id LIMIT :n`) rather than by offset on large tables, and make every paginated order unique by ending it with the primary key.

## Data

- Store times in UTC in a time zone aware type (`timestamptz` on PostgreSQL), and keep time zone aware `datetime` values in the code.
- Store money as integers of the smallest unit or as decimals, never floats; build a `Decimal` from a string, not from a float.
- Missing data is `NULL`, not `0`, an empty string or an empty object, unless the framework's convention says otherwise (Django prefers `""` for text fields); do not replace it with a computed value when you read it.
- Put constraints in the database (`NOT NULL`, foreign keys, unique indexes), not only in the code.
- Personal data is stored only where needed, and the project's retention and deletion rules apply to it.
- Back up before destructive operations, and test that restores work.
