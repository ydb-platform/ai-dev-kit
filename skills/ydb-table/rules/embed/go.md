# Go SDK (`ydb-go-sdk/v3`) — anti-patterns

Audit rules for application code talking to YDB through the Go SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own.

### RULE-GO-01: Reading "all matching rows" through Table Service without pagination

**Severity**: Critical

**What to look for**: `s.Execute(ctx, ..., "SELECT ...")` or `s.StreamExecuteScanQuery(...)` inside `db.Table().Do(...)`, with no outer keyset-pagination loop and no `res.Truncated()` check.

**Problem**: Table Service caps query results at 1000 rows by default. The cap is server-side and silent — once the matching set exceeds 1000, the call returns `err == nil` with the first 1000 rows and the rest are dropped. The bug is data-dependent: appears only when the `WHERE` clause first crosses the threshold in production, with no signal until a downstream discrepancy surfaces. The cap is a design constraint, not a knob — code must be written to exhaust the result through keyset pagination or Query Service streaming from day one. "Add a `LIMIT`" or "raise the cap" preserve the broken assumption.

**Fix**: drive the read to exhaustion through keyset pagination — an outer `for` loop wrapping `db.Query().Do(...)`, with a cursor predicate (`WHERE pk_col > $cursor ORDER BY pk_col LIMIT N`) and termination when a page returns zero rows. Read through `db.Query()` (no row cap), not `db.Table()`.

**Source**: `ydb-platform/ydb-go-sdk/MIGRATION_v2_v3.md` — section "About truncated result" documents the 1000-row default and the v3 non-retryable-error behavior. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/MIGRATION_v2_v3.md>.

### RULE-GO-02: External state mutation from inside the `Do`/`DoTx` retry closure

**Severity**: High

**What to look for**: assignments to variables declared outside the `db.Query().Do(...)` / `db.Table().Do(...)` / `DoTx(...)` lambda — `append(outerSlice, ...)`, `outerMap[k] = v`, `outerResult, err = s.Execute(...)`. Anything where state crosses the closure boundary.

**Problem**: the `Do`/`DoTx` closure is the unit of work — SDK invokes it again on every retryable error (transaction conflict, network transient, session loss). All data processing must happen *inside* the closure. Mutations to external state survive across attempts and produce wrong values: `append` to an outer slice duplicates on retry, an outer `Result` reference may end up holding a stream from a failed attempt, an outer map accumulates entries from partial reads. The closure crosses only one thing back: the success/failure decision. A value the caller needs is built atomically inside on the successful attempt and assigned to the outer variable only at the end, after the closure body has reached that line cleanly.

**Fix**: build the result inside the closure as a per-attempt local; assign to the outer variable only on the path that returns `nil`. The closure owns all data processing; only the success decision crosses the boundary.

**Source**: `ydb-platform/ydb-go-sdk` — `Do`/`DoTx` retry contract. <https://github.com/ydb-platform/ydb-go-sdk>.

### RULE-GO-03: Missing `WithIdempotent` on `Do`/`DoTx`

**Severity**: High

**What to look for**: `db.Query().Do(ctx, ...)` / `db.Table().Do(ctx, ...)` / `DoTx(ctx, ...)` calls without `query.WithIdempotent()` or `table.WithIdempotent()` in the options list.

**Problem**: the SDK classifies failures into three buckets (`retry/mode.go:MustRetry`): non-retryable (never retried), unconditionally-retryable (always retried), and **conditionally-retryable** (retried only when the developer has declared the work idempotent). The third bucket holds transport-class failures — connection drop, gRPC reset, session loss after the request was sent — where the server may have already committed the write before the failure reached the client. Replay is safe for an idempotent write (`UPSERT` keyed on an externally-generated id, idempotency-key-guarded insert) and unsafe for a non-idempotent one (counter increment, decrement, transfer, raw `INSERT` of a generated row). The SDK cannot tell which from the API surface — only the developer knows. `WithIdempotent()` is the contract: *"I declare this closure safe to replay on conditional failures."* Setting it on a non-idempotent write causes double effect; omitting it on an idempotent write makes the program propagate transport errors it could have absorbed.

**Fix**: add `query.WithIdempotent()` (or `table.WithIdempotent()`) to the `Do`/`DoTx` call when the inner work is idempotent — `UPSERT` keyed on a client-generated id, idempotency-key-guarded writes, reads. For a non-idempotent write (counter increment, transfer), the flag must *not* be set; the fix there is to make the write idempotent first — usually with a client-generated request id — and only then opt in.

**Source**: `ydb-platform/ydb-go-sdk/retry/mode.go` — `MustRetry(isOperationIdempotent bool)` returns `isOperationIdempotent` for `TypeConditionallyRetryable` errors and `true` otherwise. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/retry/mode.go>.
