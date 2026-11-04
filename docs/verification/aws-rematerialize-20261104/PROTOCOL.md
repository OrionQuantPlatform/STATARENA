# AWS relational publication workflow

Run on disposable PostgreSQL 18, original staging schema and final core/detail/support/catalog migrations. Source records include checked-in production captures, generated interleaved shards and SQL-indexed staging documents. The fixture store forbids publication through put/put_json, provider jobs, or unverified bytes. Capture every run with setup, precise inputs, results and PG log. Run before implementation, then after. No production writes.

1. Bootstrap all manifest and fixture partitions, including upcoming matches. All 13 captured endpoint families, typed core appearances/shots, standings/curated, binary asset metadata and a catalog calendar become queryable.
2. A recent 200 detail replaces an archived response while missing/error results keep the successful archive for normalization. Retain a published provider error when no successful archive exists.
3. Categorical and parameterized saved endpoints preserve their keys, error statuses and nested subjects. Upcoming fixtures need no finished-match filter.
4. Change only shots after previously published players/stats. Remove archive sources and poison the retired packed file. Prior typed player values/references and stats survive.
5. Invalid typed input halfway through a partition rolls back both core and detail updates and leaves the dirty marker for retry. A fixed retry completes.
6. A foreign DB connection changes a dirty marker during source resolution. Publication acknowledges only the captured generation. A later run processes the pending change.
7. Interleave matches from 32 shards. Each shard document/family path is opened once per processed partition. No source payload file is written.
8. --all queues complete known scope. Bounded batch and resume preserve unprocessed work. A clean repeat does not requeue all partitions or rewrite curated rows.
9. Capacity refusal before publication preserves the last generation and queued work. Database budget includes a configurable reserve.
10. Stale SQL document checksums must not publish stale bodies. Fall back only to the checksum-verified worker input store.
11. A held ingestion advisory lease prevents concurrent publication. Global catalog/support/assets changes publish even when no match partitions are dirty.

Rerun from repository root with installed dashboard Python dependencies and external embedded-postgres@18.6.0-beta.19:

```sh
node docs/verification/aws-rematerialize-20261104/run.mjs after
```

The before run imports the missing worker and must fail. Fixture SQL and source data are local. Production job progress, coverage and physical RDS growth require separate live evidence.

Deployment-role check added before role handling changes. Provision a local disposable role owning only precreated statarena_app, explicitly deny CREATE on the database, and allow SELECT on staging plus DELETE on the staging dirty marker. The complete four migrations and real fixture publication must work. No runtime grant on staging is needed.

Partial-family metadata check. After a complete typed publication remove archived and standalone match/player/stat/lineup inputs, change shots only, and poison the initial pack. The previously published stadium, per-match player coverage and collected flag must survive together with all appearance rows; no archived pack reread is allowed.

Archive-only orphan check. An indexed observation can precede its fixture row during migration. The next ordinary resume must publish its typed endpoint families without inventing a fixture, season or competition. Existing sources must remain readable.

Calendar parity. A newly saved match round must supersede the old imported calendar entry. Reindexing a changed legacy calendar must preserve the newer typed round while admitting additional calendar-only games. Both operations must be SQL-only publications.

Production privilege and source-type parity. Run the actual publisher with statarena_app owned by an administrator and the worker granted USAGE and CREATE on that schema only. Verify current_user lacks database CREATE and owns no application namespace. On partial refresh preserve the original six scalar positionId examples, including values where the same text form denotes a different source type. Measure persisted position_id_type before and after the actual worker transaction.
