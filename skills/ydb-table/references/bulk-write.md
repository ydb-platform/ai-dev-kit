# Bulk write into YDB tables

## What this is

Two YDB-level mechanisms for writing many rows at once:

- **`UPSERT INTO t SELECT … FROM AS_TABLE($list)`** — regular YQL. `AS_TABLE($list)` exposes a `List<Struct<…>>` parameter as a data source, so the upsert runs as a normal Query Service statement and is part of the surrounding transaction. Use for batches inside business operations.
- **An SDK bulk-upsert API** (commonly named `BulkUpsert`; exact symbol varies per SDK — see SDK docs) — a separate API, not YQL. The write is split into several independent transactions, each touching a single partition, executed in parallel. No cross-partition atomicity. Use for ingest / migrations where throughput matters and transactionality does not.

Sources:

- <https://ydb.tech/docs/en/yql/reference/syntax/select/from_as_table>
- <https://ydb.tech/docs/en/yql/reference/syntax/upsert_into>
- <https://ydb.tech/docs/en/dev/batch-upload>
- <https://ydb.tech/docs/en/recipes/ydb-sdk/bulk-upsert>

## Canonical pattern: `AS_TABLE`

```yql
DECLARE $items AS List<Struct<id: Uint64, value: Utf8>>;

UPSERT INTO t
SELECT id, value FROM AS_TABLE($items);
```

One query plan, one transaction, one round trip; because the query is parameterized, the server's plan cache reuses the same plan across calls.

## Operational limits of bulk-upsert

Bulk-upsert is faster than YQL `UPSERT` because it bypasses the transactional write path. That bypass costs three things — each can disqualify the API regardless of throughput:

- **No transactions.** The upstream docs state plainly: "Since no transactionality is used, this approach has a much lower overhead than YQL queries." Each partition write is independent; there is no rollback, and partial visibility across partitions is the normal state during the call.
- **Not allowed on tables with synchronous secondary indexes.** Upstream warning: "The `BulkUpsert` method isn't supported for tables with synchronous secondary indexes." Asynchronous indexes are supported (added in a later release; see the server changelog).
- **Not allowed on tables with changefeeds attached.** Writes through bulk-upsert do not flow through the CDC path; on a table with a changefeed, the call is rejected. Verify against the current target table before recommending bulk-upsert in code that may run on CDC-enabled schemas.

If any of the three applies, fall back to `AS_TABLE` (or live with a slower path that the schema can accept).

## When to use which

`AS_TABLE` for transactional batches inside a business operation — when the batch must commit or roll back atomically with the rest of the work, when the rows are read back in the same transaction, or when the target table carries synchronous secondary indexes or a changefeed.

Bulk-upsert SDK API for ingest or migrations — large initial loads, periodic refreshes, replays — where throughput is the constraint, transactionality is not required, and the target schema has no synchronous secondary index or changefeed attached.

## Related

- [`../../ydb-core/SKILL.md#schema-basics`](../../ydb-core/SKILL.md#schema-basics) — primary-key shape and partitioning determine batch-ingest efficiency.
