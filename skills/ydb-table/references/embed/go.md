# Embedding YDB in Go applications

## Stack

The only YDB Go SDK is **`github.com/ydb-platform/ydb-go-sdk/v3`**. The same package exposes two surfaces:

- a **native** API with the modern Query Service (`db.Query().Do/DoTx(...)`) and the legacy Table Service (`db.Table().Do/DoTx(...)`),
- a **`database/sql`** driver registered as `"ydb"` (blank-import `_ "github.com/ydb-platform/ydb-go-sdk/v3"`) for code that needs the stdlib interface.

Default new code to the native Query Service. The Table Service is in legacy mode and has a 1000-row silent result cap that the audit rules flag on read paths. Connection-string format and authentication environment variables: see [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting). Worked examples for both surfaces: <https://github.com/ydb-platform/ydb-go-sdk/tree/master/examples>. `database/sql` specifics: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/SQL.md>.

## Query execution

Canonical native-API pattern — open the driver once with `ydb.Open(...)`, then run all work inside a `db.Query().Do(...)` closure. The closure is the retry unit: the SDK invokes it again on every retryable error.

```go
db, err := ydb.Open(ctx, "grpc://localhost:2136/local")
if err != nil { return err }
defer db.Close(ctx)

err = db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    res, err := s.Query(ctx,
        `SELECT name FROM users WHERE id = $id;`,
        query.WithParameters(ydb.ParamsBuilder().
            Param("$id").Uint64(42).Build()),
    )
    if err != nil { return err }
    defer func() { _ = res.Close(ctx) }()
    // iterate result sets / rows, build the value inside the closure
    return nil
}, query.WithIdempotent())
```

Three load-bearing pieces:

- **`query.WithIdempotent()`** declares the closure safe to replay on *conditionally* retryable failures (connection drop, gRPC reset, session loss). Set on reads and on writes keyed by a client-generated id; do not set on a non-idempotent write such as a counter increment.
- **`query.WithParameters(ydb.ParamsBuilder()...)`** binds values rather than concatenating them. Closes SQL injection and per-distinct-text plan-cache churn. The server infers types from the builder, so a leading `DECLARE` block is optional for scalar parameters — write one only when you want an explicit contract (typically for `List<Struct<...>>` and other compound types) or to fail-fast on a parameter-type mismatch from the caller.
- **All data processing happens inside the closure.** Assign to outer variables only on the success path — the line that returns `nil`. Anything assigned earlier survives across retry attempts and produces wrong values.

Source: <https://github.com/ydb-platform/ydb-go-sdk> README "Example Usage".

## Transactions

YDB has two transaction styles, and `ydb-go-sdk/v3` supports both:

- **Non-interactive** (default for new code) — the SDK manages the transaction inside `db.Query().DoTx(ctx, func(ctx, tx query.TxActor) error { ... })`. Per the upstream `query/client.go` godoc: *"If op TxOperation returns nil — transaction will be committed"*. Open the driver with `ydb.WithLazyTx(true)` so the begin is deferred onto the first query, and pass `query.WithCommit()` to the last write so the commit rides on its RPC — zero standalone begin/commit round-trips.
- **Interactive** — the developer writes `s.BeginTransaction(...)` and `tx.CommitTx(...)`. Same fusing, achieved by passing a `*table.TransactionControl` as the positional second argument of `s.Execute(...)` instead of running a standalone Begin first: `s.Execute(ctx, table.TxControl(table.BeginTx(table.WithSerializableReadWrite()), table.CommitTx()), query, params)` — a single RPC carries begin + write + commit. On the Query Service, the equivalent is `s.Query(ctx, sql, query.WithTxControl(...), query.WithCommit())` (txControl and commit are `ExecuteOption`s). Canonical Table Service form: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/ttl/series.go>.

Worked non-interactive example: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/transaction/query/main.go>.

For the transaction-mode list (`SerializableRW`, `SnapshotRO`, `StaleRO`, `OnlineRO`) and the consequence for application-level optimistic locking, see [`../working-with-data.md`](../working-with-data.md).

## Retries

`Do` / `DoTx` retry the closure internally; there is no need for an outer `for` loop or a `time.Sleep`-based retrier in caller code. The SDK classifies the error through `retry/mode.go` `MustRetry(isOperationIdempotent bool)`:

- **Non-retryable** — propagated to the caller (`PRECONDITION_FAILED`, schema mismatch, bad parameters).
- **Unconditionally retryable** — always retried regardless of idempotency (`ABORTED`, `OVERLOADED`).
- **Conditionally retryable** — retried only when `WithIdempotent` was passed (transport drops, session loss, timeouts).

Backoff and jitter are built in; configure via retry options on the `Do` / `DoTx` call, not by wrapping.

Source: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/mode.go>.

## Bulk upsert

Use `db.Table().BulkUpsert(ctx, tablePath, rows)` for non-transactional ingest:

```go
err := db.Table().BulkUpsert(ctx,
    path.Join(db.Name(), "events"),
    table.BulkUpsertDataRows(types.ListValue(values...)),
)
```

For when the bulk API is the right call versus `AS_TABLE` inside a transaction — and when it is forbidden (synchronous secondary indexes, attached changefeeds) — see [`../working-with-data.md`](../working-with-data.md).

Source: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/opensource_night2024/main.go>.

## Connection

See [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting).
