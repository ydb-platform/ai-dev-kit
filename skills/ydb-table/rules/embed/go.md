# Go SDK (`ydb-go-sdk/v3`) — anti-patterns

Audit rules for application code talking to YDB through the Go SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own.

### RULE-GO-01: Reading "all matching rows" through Table Service without pagination

**Severity**: Critical

**What to look for**: `s.Execute(ctx, ..., "SELECT ...")` or `s.StreamExecuteScanQuery(...)` inside `db.Table().Do(...)`, with no outer keyset-pagination loop. Also any `ydb.WithIgnoreTruncated` on the driver — that option silences the v3 error and restores v2-style silent truncation, which is what the rule exists to prevent.

**Problem**: Table Service caps query results at 1000 rows by default. In v3 the cap surfaces — `s.Execute` returns a non-retryable error and `s.StreamExecuteScanQuery` returns a retryable one (so it loops until the retry budget exhausts). Either way the code does not get the full result set. The architectural problem is that code written assuming "one `Execute` returns everything matching" is wrong by construction: it works in dev with small data, errors out in production once the match crosses the cap, and the common reflex — pass `ydb.WithIgnoreTruncated` to "fix" the error — restores v2-style silent truncation where the call returns `err == nil` with the first 1000 rows of the match and everything beyond the cap dropped on the floor, and downstream code under-bills / under-processes without any signal. The cap is a design constraint, not a knob.

**Fix**: drive the read to exhaustion through keyset pagination — an outer `for` loop wrapping `db.Query().Do(...)`, with a cursor predicate (`WHERE pk_col > $cursor ORDER BY pk_col LIMIT N`) and termination when a page returns zero rows. Read through `db.Query()` (Query Service streams without the row cap), not `db.Table()`. Adding `ydb.WithIgnoreTruncated` is not a fix.

**Source**: `ydb-platform/ydb-go-sdk/MIGRATION_v2_v3.md` — section "About truncated result" documents the 1000-row default and the v3 non-retryable-error behavior. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/MIGRATION_v2_v3.md>.

### RULE-GO-02: External state mutation from inside the `Do`/`DoTx` retry closure

**Severity**: High

**What to look for**: mutations of state outside the `db.Query().Do(...)` / `db.Table().Do(...)` / `DoTx(...)` lambda *while the closure is still running* — `append(outerSlice, row)` mid-iteration, `outerMap[k] = v` after each row, `outerResult, err = s.Execute(...)` capturing a per-attempt handle, an external side effect like a charge / RPC / log emission called from inside the closure body. The single allowed pattern is the final `outerVar = local` assignment on the success path, immediately before the closure returns `nil` — that one is what the Fix prescribes and must not be flagged.

**Problem**: the `Do`/`DoTx` closure is the unit of work — SDK invokes it again on every retryable error (transaction conflict, network transient, session loss). All data processing must happen *inside* the closure. Mutations to external state survive across attempts and produce wrong values: `append` to an outer slice duplicates on retry, an outer `Result` reference may end up holding a stream from a failed attempt, an outer map accumulates entries from partial reads. The closure crosses only one thing back: the success/failure decision. A value the caller needs is built atomically inside on the successful attempt and assigned to the outer variable only at the end, after the closure body has reached that line cleanly.

**Fix**: build the result inside the closure as a per-attempt local; assign to the outer variable only on the path that returns `nil`. The closure owns all data processing; only the success decision crosses the boundary.

**Source**: `ydb-platform/ydb-go-sdk` — `Do`/`DoTx` retry contract in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/client.go> (godocs on `Do` / `DoTx`) and the retry loop in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/retry.go>.

### RULE-GO-03: Missing `WithIdempotent` on `Do`/`DoTx`

**Severity**: High

**What to look for**: `db.Query().Do(ctx, ...)` / `db.Table().Do(ctx, ...)` / `DoTx(ctx, ...)` calls whose closure body is safe to replay (a read; an `UPSERT` keyed on a value the caller already has — externally-generated id, idempotency key; a write guarded by such a key) but no `query.WithIdempotent()` / `table.WithIdempotent()` in the options list. Do *not* flag calls where the closure body is non-idempotent (counter increment, money transfer, raw `INSERT` of a generated row) — there `WithIdempotent` must remain absent and the fix is to make the work idempotent first.

**Problem**: the SDK classifies failures into three buckets (`retry/mode.go:MustRetry`): non-retryable (never retried), unconditionally-retryable (always retried), and **conditionally-retryable** (retried only when the developer has declared the work idempotent). The third bucket holds transport-class failures — connection drop, gRPC reset, session loss after the request was sent — where the server may have already committed the write before the failure reached the client. Replay is safe for an idempotent write (`UPSERT` keyed on an externally-generated id, idempotency-key-guarded insert) and unsafe for a non-idempotent one (counter increment, decrement, transfer, raw `INSERT` of a generated row). The SDK cannot tell which from the API surface — only the developer knows. `WithIdempotent()` is the contract: *"I declare this closure safe to replay on conditional failures."* Setting it on a non-idempotent write causes double effect; omitting it on an idempotent write makes the program propagate transport errors it could have absorbed.

**Fix**: add `query.WithIdempotent()` (or `table.WithIdempotent()`) to the `Do`/`DoTx` call when the inner work is idempotent — `UPSERT` keyed on a client-generated id, idempotency-key-guarded writes, reads. For a non-idempotent write (counter increment, transfer), the flag must *not* be set; the fix there is to make the write idempotent first — usually with a client-generated request id — and only then opt in.

**Source**: `ydb-platform/ydb-go-sdk/retry/mode.go` — `MustRetry(isOperationIdempotent bool)` returns `isOperationIdempotent` for `TypeConditionallyRetryable` errors and `true` otherwise. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/mode.go>.

### RULE-GO-04: `for` loop wrapping `db.Query().Do(...)` / `db.Table().Do(...)`

**Severity**: High

**What to look for**: an outer `for` / `for { ... }` / `for i := 0; i < N; i++` block whose body calls `db.Query().Do(ctx, ...)` or `db.Table().Do(ctx, ...)` and decides whether to repeat based on the returned error.

**Fix**: remove the outer loop. `Do`/`DoTx` already classifies errors via `retry/mode.go` and replays the closure on retryable failures. An outer loop multiplies backoff, re-runs work on non-retryable errors the SDK has correctly decided not to retry, and breaks the SDK's retry budget. If the goal is "retry forever on a specific class" — pass it through `WithIdempotent` / retry options, not by wrapping.

**Source**: `ydb-platform/ydb-go-sdk/retry/retry.go` — `Retry` / `Do` / `DoTx` implement the retry loop internally with classified backoff. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/retry.go>.

### RULE-GO-05: Custom retrier with `time.Sleep` wrapping YDB calls

**Severity**: High

**What to look for**: `for` loop with explicit `time.Sleep(...)` between attempts, calling any YDB-facing method inside — session methods (`s.Execute`, `s.Query`, `s.BeginTransaction`), client-level methods (`db.Table().CreateSession`, `db.Table().Do`, `db.Query().Do`, `db.Query().DoTx`), or arbitrary user functions that themselves call into the SDK.

**Fix**: delete the custom loop and use the SDK retrier (`db.Query().Do`, `db.Table().Do`, `retry.Retry` from `retry/`). A hand-rolled retrier doesn't see YDB's error classification — it replays every non-nil error indiscriminately: non-retryable failures (`PRECONDITION_FAILED`, schema mismatch) burn the retry budget, and conditionally-retryable failures (transport drops where the server may have committed) get retried with no idempotency gate, which can double-apply a non-idempotent write. The SDK retrier classifies via `retry/mode.go` `MustRetry(isOperationIdempotent bool)` and only retries the conditional bucket when `WithIdempotent` is set. Backoff with jitter and session-pool integration also come from the SDK retrier, not from caller-side `for`/`Sleep` code.

**Source**: `ydb-platform/ydb-go-sdk` — retry classification in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/mode.go>; retry loop and backoff in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/retry.go> and <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/backoff.go>.

### RULE-GO-06: Nested `Do` / `DoTx` call

**Severity**: Critical

**What to look for**: a `db.Query().Do(...)` or `db.Table().Do(...)` (or `DoTx`) appearing inside another `Do`/`DoTx` lambda. Any "retrier inside a retrier" shape.

**Fix**: pass the session (`s`) through the call chain instead of opening a new retry scope. The inner `Do` checks out an independent session from the pool — under load this races for pool slots and can starve the caller; under retry it multiplies attempts combinatorially with the outer scope. Helpers called from inside a `Do` lambda must take `query.Session` (or `table.Session`) as a parameter and use the passed session directly.

**Source**: `ydb-platform/ydb-go-sdk/retry/retry.go` — `Do` pool checkout semantics. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/retry.go>.

### RULE-GO-07: Non-parametrized YQL — `fmt.Sprintf` / string concat into query text

**Severity**: Critical

**What to look for**: `fmt.Sprintf` building a query string, `"SELECT ... " + variable` concatenation, `text/template` rendering of a query body. Anything where caller values appear inside the YQL literal rather than as bound parameters.

**Fix**: bind values through `ydb.ParamsBuilder().Param("$name").<Type>(value).Build()` and pass them via `query.WithParameters(...)` (or `table.NewQueryParameters(...)` for Table Service). Two failure modes the SDK's parameter API closes: SQL injection (caller values become YQL syntax when concatenated), and per-call query-plan miss (every distinct rendered text is a new plan in the server-side cache). A `DECLARE` block in the query body is optional — types are inferred from the bound values — and is justified when the parameter shape is compound (`List<Struct<...>>`) or when an explicit caller contract is desirable.

**Source**: `ydb-platform/ydb-go-sdk` — `ParamsBuilder` in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/params_builder.go>; `query.WithParameters` in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/execute_options.go>. YQL parameters reference: <https://ydb.tech/docs/en/yql/reference/syntax/declare>.

### RULE-GO-08: `PreferLocalDC` / `PreferNearestDC` balancer in production

**Severity**: High

**What to look for**: `ydb.WithBalancer(balancers.PreferLocalDC(...))` or `ydb.WithBalancer(balancers.PreferNearestDC(...))` (the rename — `PreferLocalDC` is marked `// Deprecated`, but `PreferNearestDC` has the same effect) in driver construction.

**Fix**: drop the `WithBalancer(...)` option (or use `balancers.RandomChoice()` explicitly — that is what `balancers.Default()` returns). Prefer-DC balancers concentrate all client traffic on nodes in one datacenter — the "local" / "nearest" one — turning the cluster's other DCs into idle hot-standbys and the chosen DC into a saturation bottleneck. Cross-DC latency savings on individual requests are dwarfed by the throughput cliff once the chosen DC's nodes are saturated. `RandomChoice` picks an endpoint at random per request and spreads load evenly across every available node in the cluster.

**Source**: `ydb-platform/ydb-go-sdk/balancers/balancers.go` — `PreferLocalDC` is marked `// Deprecated: use PreferNearestDC instead`; both have the same balancing semantics. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/balancers/balancers.go>.

### RULE-GO-09: Transaction begin as a separate RPC

**Severity**: Medium

YDB supports two transaction styles. *Interactive* — the developer writes `begin` and `commit` calls. *Non-interactive* — the SDK manages the transaction inside `DoTx`; the developer influences it via options. In either mode, the begin can ride on the first query's RPC instead of being its own RPC.

**What to look for**:

- *Interactive*: `s.BeginTransaction(ctx, ...)` or `s.Begin(ctx, ...)` returning a `tx` handle, followed by `tx.Exec(...)` / `tx.Query(...)` (Query Service) or `tx.Execute(...)` (Table Service).
- *Non-interactive*: `db.Query().DoTx(...)` (or `db.Table().DoTx(...)`) on a driver opened without `ydb.WithLazyTx(true)`.

**Fix**:

- *Interactive*: drop the standalone `s.BeginTransaction(...)` and let the begin ride on the first query.
  - Table Service: the first call is `tx, result, err := s.Execute(ctx, table.TxControl(table.BeginTx(table.WithSerializableReadWrite())), firstQuery, params)` — `txControl` is the positional second argument; the returned `tx` is then used for subsequent `tx.Execute(...)` calls within the transaction (single-shot autocommit also exists: add `table.CommitTx()` to the same `TxControl` if the transaction has just one statement).
  - Query Service: `s.Query(ctx, firstQuery, query.WithTxControl(tx.NewControl(tx.BeginTx(tx.WithSerializableReadWrite()))), query.WithParameters(...))`.
- *Non-interactive*: open the driver with `ydb.WithLazyTx(true)` (or pass `query.WithLazyTx(true)` as a per-call `DoTxOption`). `DoTx` then defers begin to the first query inside the closure.

**Source**: `Session.Execute(ctx, *TransactionControl, sql, *params.Params, ...)` returns `(Transaction, Result, error)` — <https://github.com/ydb-platform/ydb-go-sdk/blob/master/table/table.go>. Canonical multi-statement form: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/table/example_test.go> (`Example_lazyTransaction`). `ydb.WithLazyTx` driver option: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/options.go>; per-call `query.WithLazyTx`: <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/client.go>.

### RULE-GO-10: Transaction commit as a separate RPC

**Severity**: Medium

Same split as RULE-GO-09. In either transaction style the commit can ride on the last query's RPC.

**What to look for**:

- *Interactive*: `tx.Commit(ctx)` / `tx.CommitTx(ctx)` called as a separate statement after the last `tx.Exec(...)` / `tx.Query(...)` (Query Service) or `tx.Execute(...)` (Table Service).
- *Non-interactive*: `db.Query().DoTx(ctx, func(...) { ...; return nil })` where the last write inside the closure does not carry `query.WithCommit()`. `DoTx` will commit on return-nil, but as its own RPC.
- *Doubly wrong*: an explicit `tx.CommitTx(ctx)` call **inside** a `DoTx` closure. `DoTx` already commits on return-nil per `query/client.go:DoTx` godoc; the explicit call is both redundant and a separate RPC.

**Fix**: fuse the commit into the last query's RPC.

- Query Service: pass `query.WithCommit()` as an `ExecuteOption` to the last `tx.Exec(...)` / `tx.Query(...)` of the closure.
- Table Service (multi-statement interactive transaction): pass `options.WithCommit()` (from `github.com/ydb-platform/ydb-go-sdk/v3/table/options`) as an `ExecuteDataQueryOption` to the last `tx.Execute(ctx, sql, params, options.WithCommit())` — the commit flag rides on that RPC and the transaction terminates without a separate `tx.CommitTx`. For a single-statement Table Service transaction, fold both begin and commit into one `s.Execute(ctx, table.TxControl(table.BeginTx(...), table.CommitTx()), sql, params)`.

For the doubly-wrong case (explicit `tx.CommitTx` inside a `DoTx` closure), also delete the call — `DoTx` handles commit on return-nil.

**Source**: `query.WithCommit() ExecuteOption` — <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/execute_options.go>; `DoTx` godoc *"If op TxOperation returns nil - transaction will be committed"* — <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/client.go>. Table Service `options.WithCommit() ExecuteDataQueryOption` — <https://github.com/ydb-platform/ydb-go-sdk/blob/master/table/options/options.go>; canonical multi-statement usage in <https://github.com/ydb-platform/ydb-go-sdk/blob/master/table/example_test.go> (`Example_lazyTransaction`) and <https://github.com/ydb-platform/ydb-go-sdk/blob/master/tests/integration/table_tx_lazy_test.go>.
