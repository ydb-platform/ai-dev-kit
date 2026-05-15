# YDB transaction modes

## What this is

The Query Service supports four transaction modes:

- **`SerializableRW`** — the default. Read-write, server-side serializable. YDB uses optimistic concurrency control: conflicting transactions are detected by the server at commit time and surface as a retryable `ABORTED` status with the message `Transaction locks invalidated`.
- **`SnapshotRO`** — read-only, sees a consistent snapshot. Does not coordinate with concurrent writers.
- **`StaleRO`** — read-only, reads from any replica; may return stale data.
- **`OnlineRO`** — read-only, reads from the leader.

Source: <https://ydb.tech/docs/en/concepts/transactions>.

## Implication: application-level optimistic locking is redundant

The Postgres / Read-Committed pattern of carrying a `version` column and emitting `UPDATE … WHERE … AND version = ?` to catch lost updates is unnecessary under `SerializableRW`: the server already detects the conflict and surfaces it as a retryable failure (`ABORTED` / `Transaction locks invalidated`). The extra predicate adds work on every UPDATE and provides no additional safety — the correct response to a conflict is to retry the transaction, which the SDK retry helpers already do for `ABORTED`.

## Read-only loads

For purely read workloads, `SnapshotRO` is the right default — it reduces coordination cost with writers while still seeing a consistent view. Use `StaleRO` only when bounded staleness is acceptable in exchange for lower latency, and `OnlineRO` when you need to read from the leader (e.g., to observe the freshest committed state without participating in a read-write transaction).

Note: reads against column-oriented tables are restricted to `SerializableRW` and `SnapshotRO`; `StaleRO` and `OnlineRO` are not supported for column-oriented reads.

## Related

- [`../../ydb-core/SKILL.md#schema-basics`](../../ydb-core/SKILL.md#schema-basics) — schema choices interact with transaction cost (partition locality).
