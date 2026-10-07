# Database guidelines for services

The database outlives every version of the code. Treat changes to it as the riskiest part of a release.

## Migrations

- Every schema change is a migration in the repository, reviewed like code and applied by the deploy, never by hand.
- A migration must work while the previous version of the service is still running. Split breaking changes into steps across releases, for example: add the new column, write to both, backfill, switch reads, then drop the old column.
- Never edit a migration that has run anywhere shared; write a new one.
- Large backfills and index builds run in batches or concurrently, outside the transaction that changes the schema, so they do not lock tables for long.
- Make migrations reversible where you can, and say in the pull request when one is not.

## Queries

- Use bound parameters for every value; never build SQL by formatting strings.
- Keep transactions short and never wait on the network inside one.
- Watch for N+1 queries: load related data in one query or a batch.
- Every query on a large table uses an index; check the plan of new queries against realistic data.
- Paginate by key (`WHERE id > :last ORDER BY id LIMIT :n`) rather than by offset on large tables.

## Data

- Store times in UTC with their time zone type, money as integers or decimals, never floats.
- Put constraints in the database (`NOT NULL`, foreign keys, unique indexes), not only in the code.
- Personal data is stored only where needed, and the project's retention and deletion rules apply to it.
- Back up before destructive operations, and test that restores work.
