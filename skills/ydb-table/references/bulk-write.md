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

## When to use which

`AS_TABLE` for transactional batches inside a business operation — when the batch must commit or roll back atomically with the rest of the work, or when the rows are read back in the same transaction.

Bulk-upsert SDK API for ingest or migrations — large initial loads, periodic refreshes, replays — where throughput is the constraint and partial visibility across partitions is acceptable. The upstream docs describe it as "more efficient than plain YQL" for this case.

## Related

- [`../../ydb-core/SKILL.md#schema-basics`](../../ydb-core/SKILL.md#schema-basics) — primary-key shape and partitioning determine batch-ingest efficiency.
