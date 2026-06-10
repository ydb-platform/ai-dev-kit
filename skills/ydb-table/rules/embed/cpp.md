# C++ SDK (`ydb-cpp-sdk`) — anti-patterns

Audit rules for application code talking to YDB through the C++ SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own. For positive patterns, see [`../../references/embed/cpp.md`](../../references/embed/cpp.md).

### RULE-CPP-01: Reading "all matching rows" through Table Service `ExecuteDataQuery` without pagination

**Severity**: Critical

**What to look for**: `session.ExecuteDataQuery(...)` on `NYdb::NTable::TSession` where the read is **intended to exhaust a result set** — an unbounded `SELECT` (no key-equality `WHERE`), a range predicate over many rows, anything followed by a `TResultSetParser` loop that processes the full match — and there is no check of `TResultSet::Truncated()`, no outer keyset-pagination loop, and no `StreamExecuteScanQuery`. A bounded point read (`WHERE id = $id` with a single key) or a small explicit `LIMIT` where the caller cannot accept more rows by construction is not the target. `StreamExecuteScanQuery` and Query Service `StreamExecuteQuery` are *not* targets — they are the legitimate streaming paths.

**Problem**: Table Service `ExecuteDataQuery` caps its result set; `TResultSet::Truncated()` signals the match was cut off. Code that assumes one call returns everything matching will under-process in production once the match exceeds the cap. Ignoring `Truncated()` or never paginating is the same structural failure as silently dropping rows. (Query Service `StreamExecuteQuery` does not set `Truncated()` the same way — it streams `ReadNext()` parts. This rule is scoped to `ExecuteDataQuery`; the streaming path has its own concern, RULE-CPP-09.)

**Fix** — pick one of three structural paths:

- **Switch to Query Service streaming**: rewrite through `TQueryClient::StreamExecuteQuery` and iterate `ReadNext()` parts (design for possible duplicate rows on retry — see RULE-CPP-09).
- **Keyset-paginate**: wrap the call in an outer loop with a cursor predicate and `ORDER BY` over the table's primary key; terminate when a page returns zero rows. The loop continuation is driven by rows / cursor, not by retry status — see RULE-CPP-04.
- **Table scan stream**: use `StreamExecuteScanQuery` when staying on the Table client.

**Source**: YDB docs — paging guide at <https://ydb.tech/docs/en/dev/paging> (keyset pagination over the primary key, the canonical strategy). The `TResultSet::Truncated()` flag the rule keys on is part of the public C++ API in `include/ydb-cpp-sdk/client/result/result.h`.

### RULE-CPP-02: External state mutation from inside the retry lambda

**Severity**: High

**What to look for**: mutations of state outside the `RetryQuerySync` / `RetryOperationSync` lambda *while the lambda is still running* — `outerVec.push_back(row)` mid-iteration, `outerMap[k] = v` after each row, capturing a per-attempt result handle into an outer reference before the lambda returns success, emitting side effects (RPC, log, charge) from inside the lambda body. The single allowed pattern is the final `outerVar = local` assignment on the success path, immediately before the lambda returns a successful `TStatus` — that one is what the Fix prescribes and must not be flagged.

**Problem**: the retry lambda is the unit of work — the SDK invokes it again on every retryable error (`ABORTED`, `UNAVAILABLE`, `BAD_SESSION`, etc.). Mutations to external state survive across attempts and produce wrong values: `push_back` duplicates on retry, an outer result reference may hold a stream from a failed attempt, an outer map accumulates entries from partial reads. Build the result as a per-attempt local; assign to the outer variable only when returning success.

**Fix**: build the result inside the lambda as a per-attempt local; assign to the outer variable only on the path that returns a successful `TStatus`. The lambda owns all data processing; only the success decision crosses the boundary.

**Source**: YDB docs — retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> (the SDK retries the user-supplied lambda as the unit of work); error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>. The C++ retrier that drives the replay is `RetryQuerySync` in `include/ydb-cpp-sdk/client/query/client.h`.

### RULE-CPP-03: Missing `.Idempotent(true)` on `RetryQuerySync` / `RetryOperationSync`

**Severity**: High

**What to look for**: a mismatch between the lambda's idempotency and the setting in either direction.

- **Missing flag on safe-to-replay work**: `RetryQuerySync` / `RetryOperationSync` whose lambda body is replay-safe (a read; an `UPSERT` keyed on a value the caller already has; a write guarded by an idempotency key) but no `NYdb::NRetry::TRetryOperationSettings().Idempotent(true)` passed as the settings argument. Fix: add `.Idempotent(true)`.
- **Flag set on non-idempotent work**: retry call carrying `.Idempotent(true)` while the lambda performs a non-idempotent write (counter increment, money transfer, raw `INSERT` of a generated row). Fix: remove the flag *and* rework the write to be idempotent before opting back in.

**Problem**: per the YDB docs, `UNDETERMINED` is conditionally retryable — "only idempotent operations can be fixed with a retry." These are failures where the server may have already committed the write before the client saw the failure. The SDK cannot infer idempotency from the API surface — only the developer knows. Setting the flag on a non-idempotent write causes double effect on retry; omitting it on an idempotent write makes the program propagate errors it could have absorbed.

**Fix**: pass `NYdb::NRetry::TRetryOperationSettings().Idempotent(true)` (or `NYdb::NTable::TRetryOperationSettings().Idempotent(true)`) when the inner work is idempotent. For non-idempotent writes, do not set the flag; make the write idempotent first (client-generated request id, dedup guard) before opting in.

**Source**: YDB docs — status-code retry table at <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes> (UNDETERMINED is conditionally retryable for idempotent operations only; PRECONDITION_FAILED non-retryable); retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> ("Idempotent operations are retried for a broader range of errors"); error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling> ("Only idempotent operations can be fixed with a retry").

### RULE-CPP-04: `for` loop wrapping `RetryQuerySync` / `RetryOperationSync` for retry purposes

**Severity**: High

**What to look for**: an outer `for` / `while` block whose body calls `RetryQuerySync` or `RetryOperationSync` and **decides whether to repeat based on the returned `TStatus`** (success-or-error). Common shapes: `for (int attempt = 0; attempt < N; ++attempt) { status = client.RetryQuerySync(...); if (status.IsSuccess()) break; }`, or a `while (!status.IsSuccess())` wrapper.

**Not a target**: a keyset-pagination outer loop whose continuation depends on rows returned, a cursor advancing, or an `EOS` flag — even though it also wraps `RetryQuerySync` (see RULE-CPP-01 fix). The signal is what drives the next iteration, not the loop syntax.

**Problem**: `RetryQuerySync` / `RetryOperationSync` already retry the lambda internally with status-classified backoff. A status-driven outer loop multiplies the backoff schedule, re-runs work on non-retryable errors the SDK has correctly decided not to retry, and silently inflates the retry budget the caller thinks they configured. The YDB error-handling guide is explicit: "Do not use endless retries" and "do not repeat instant retries more than once."

**Fix**: remove the outer status-driven loop. Express tuning through `TRetryOperationSettings` (`MaxRetries`, `MaxTimeout`, `FastBackoffSettings`, `SlowBackoffSettings`), not by wrapping the SDK retrier.

**Source**: YDB docs — retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> (the SDK provides the retrier; C++ `TRetryOperationSettings` knobs are listed there: `MaxRetries`, `MaxTimeout`, `FastBackoffSettings`, `SlowBackoffSettings`, `RetryNotFound`); excess-retry guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>.

### RULE-CPP-05: Custom retrier with `Sleep` wrapping YDB calls

**Severity**: High

**What to look for**: `for` loop with explicit `Sleep` / `std::this_thread::sleep_for` / manual backoff between attempts, calling any YDB-facing method inside — `session.ExecuteQuery`, `session.ExecuteDataQuery`, `client.GetSession`, `BulkUpsert`, or arbitrary helpers that call into the SDK.

**Problem**: a hand-rolled retrier replays every non-success `TStatus` indiscriminately. Non-retryable failures (`PRECONDITION_FAILED`, `SCHEME_ERROR`, `BAD_REQUEST`) burn the retry budget on errors that will never recover; conditionally-retryable failures (`UNDETERMINED`) get retried with no idempotency gate, which can double-apply a non-idempotent write. The YDB docs are explicit that the SDK ships a built-in retry mechanism for exactly this reason and that idempotency must be opted into per call.

**Fix**: delete the custom loop and use `RetryQuerySync` / `RetryOperationSync`; express tuning through `TRetryOperationSettings` rather than caller-side `for` / `Sleep` code.

**Source**: YDB docs — retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> ("YDB SDKs provide built-in tools for retries"); status-code classification at <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes>; error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>.

### RULE-CPP-06: `NYdb::TDriver` constructed per request instead of once per process

**Severity**: High

**What to look for**: `NYdb::TDriver` (or a `TDriverConfig` that immediately feeds one) constructed **inside** a request handler, controller method, RPC stub body, per-iteration of a worker loop, or any per-call helper that talks to YDB — then used to build a `TQueryClient` / `TTableClient` for a single piece of work. The grep signal is `TDriver driver(...)` or `NYdb::TDriver(...)` inside a function that is called more than once during the process lifetime. A driver constructed once at program startup (e.g. in `main`) and threaded to handlers is *not* the target.

**Problem**: `TDriver` owns the gRPC channel pool, endpoint-discovery state, and background worker threads. Constructing one per request pays full endpoint discovery, gRPC channel setup, and TLS handshake before every YDB call, then tears the state back down — a latency cliff under any non-trivial RPS and a connection-churn signal at the cluster. Failing to call `driver.Stop(true)` on the short-lived driver also leaks the background threads.

**Fix**: hold a single `NYdb::TDriver` for the process lifetime (build it at startup, stop it at shutdown via `driver.Stop(true)`); pass it to surface clients (`TQueryClient`, `TTableClient`) which are cheap to construct on demand.

**Source**: YDB docs — SDK initialization recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/init> (the canonical shape: one driver constructed at startup, deferred close at shutdown, clients built on top). `TDriver` lifecycle surface in `include/ydb-cpp-sdk/client/driver/driver.h` of `ydb-platform/ydb-cpp-sdk`.

### RULE-CPP-07: Non-parametrized YQL — `std::format` / string concat into query text

**Severity**: Critical

**What to look for**: `std::format` / `fmt::format` building a query string, `"SELECT ... " + variable` concatenation, rendering caller values into the YQL literal rather than binding them through `TParamsBuilder`.

**Problem**: two failure modes the SDK's parameter API closes at once. Injection — caller values become YQL syntax when concatenated. Per-call query-plan miss — YDB's query-compilation cache works best with stable query text; every distinct rendered string defeats reuse and forces re-compilation work on the server.

**Fix**: bind values through `TParamsBuilder().AddParam("$name").<Type>(value).Build()` and pass the resulting `TParams` to `ExecuteQuery` / `ExecuteDataQuery`. A `DECLARE` block in the query body is optional for scalars — types are inferred from bound values — and is justified for compound shapes (`List<Struct<...>>`).

**Source**: YDB docs — parameterized queries guide at <https://ydb.tech/docs/en/reference/ydb-sdk/parameterized_queries> ("saves from vulnerabilities like SQL Injection" and "cache the query plan for parameterized requests"); YQL `DECLARE` syntax at <https://ydb.tech/docs/en/yql/reference/syntax/declare>. C++ binding surface is `TParamsBuilder` in `include/ydb-cpp-sdk/client/params/params.h`.

### RULE-CPP-08: Explicit `BeginTransaction` + `Commit` when fused `TTxControl` suffices

**Severity**: Medium

**What to look for**: `session.BeginTransaction(...)` followed by one `ExecuteQuery` / `ExecuteDataQuery` and `tx.Commit()` for **single-statement** work where `TTxControl::BeginTx(...).CommitTx()` on the query call would fuse begin, execute, and commit into fewer round trips. Multi-step flows that genuinely need client logic between statements (as in `MultiStep` in the basic example) are not the target.

**Problem**: separate begin and commit RPCs add latency and session churn. Per the YDB transactions guide, "if the transaction body is fully formed before accessing the database, it will be processed more efficiently" — fused `TTxControl::BeginTx(...).CommitTx()` lets the server execute the statement and commit in a single round trip; the explicit `BeginTransaction` / `Commit()` split forces two extra hops with no semantic gain for a single statement.

**Fix**: for single-statement transactions, pass `TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()` as the second argument to `ExecuteQuery` / `ExecuteDataQuery` instead of explicit `BeginTransaction` + `Commit()`.

**Source**: YDB docs — transactions guide at <https://ydb.tech/docs/en/concepts/transactions> ("if the transaction body is fully formed before accessing the database, it will be processed more efficiently"). C++ `TTxControl` API in `include/ydb-cpp-sdk/client/query/tx.h` of `ydb-platform/ydb-cpp-sdk`.

### RULE-CPP-09: `StreamExecuteQuery` consumer assumes exactly-once rows

**Severity**: High

**What to look for**: `StreamExecuteQuery` / `TExecuteQueryIterator::ReadNext` loop that processes rows with no deduplication strategy, no idempotent sink, and no comment acknowledging retry-induced duplicates — especially when the stream call sits inside or under `RetryQuerySync`.

**Problem**: the SDK retrier replays the user-supplied lambda as a whole on retryable errors; a stream that already emitted N rows before the failure will, on the next attempt, emit those rows again before reaching new ones. A consumer that counts rows, bills per row, or appends to an external queue without dedupe will double-count on replay.

**Fix**: design the sink to be idempotent (keyed UPSERT, dedup by primary key), or track the last-seen cursor and skip duplicates. Do not assume one physical row per logical row in a retried stream.

**Source**: YDB docs — retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> (the SDK retries the lambda as the unit of work, so partial side effects from a failed attempt are observable again on the next); error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>.

### RULE-CPP-10: `INSERT INTO` inside a retry lambda with `.Idempotent(true)`

**Severity**: High

**What to look for**: a YQL query string starting with `INSERT INTO` executed by `session.ExecuteQuery` / `session.ExecuteDataQuery` inside the lambda body of `RetryQuerySync` / `RetryOperationSync` **whose settings carry `.Idempotent(true)`**. The grep pair is `INSERT INTO` co-located with `TRetryOperationSettings().Idempotent(true)`. A `RetryQuerySync` without the flag is not the target — that's RULE-CPP-03's other half.

**Problem**: `INSERT INTO` in YDB fails with `PRECONDITION_FAILED` (`Operation aborted due to constraint violation: insert_pk`) when the primary key already exists. `.Idempotent(true)` enables the SDK retrier to replay on `UNDETERMINED` / `TRANSPORT_UNAVAILABLE` — situations where the **first attempt may have already committed**. The replay then hits `PRECONDITION_FAILED`, the SDK surfaces it as a non-retryable terminal status, and the caller sees a hard failure for a write that did in fact land. Net effect: a write that succeeded looks failed; downstream compensations / re-tries propagate the wrong outcome.

**Fix**: pick one — (a) switch the statement to `UPSERT INTO` (replay-safe by construction; converges to the same final state), (b) keep `INSERT INTO` and drop `.Idempotent(true)` so the SDK propagates `UNDETERMINED` instead of replaying, or (c) wrap the INSERT in a server-side idempotency guard (existence check + INSERT in one transaction, or a dedup table keyed on a client-generated request id) before opting back into `.Idempotent(true)`.

**Source**: YDB docs — status-code retry table at <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes> (UNDETERMINED conditionally retryable for idempotent operations; PRECONDITION_FAILED non-retryable); YQL `INSERT` semantics at <https://ydb.tech/docs/en/yql/reference/syntax/insert_into> (duplicate primary key surfaces as `PRECONDITION_FAILED` / `insert_pk`); error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling> ("Only idempotent operations can be fixed with a retry").

### RULE-CPP-11: DDL (`ExecuteSchemeQuery` / `CreateTable`) executed inside a `RetryQuerySync` / `RetryOperationSync` lambda

**Severity**: Medium

**What to look for**: `session.ExecuteSchemeQuery(...)` or `tableClient.CreateTable(...)` (or a YQL string beginning with `CREATE TABLE` / `ALTER TABLE` / `DROP TABLE` passed to a query-execute call) appearing inside the lambda body of `RetryQuerySync` / `RetryOperationSync` — typically alongside DML on the same retry path. DDL run *outside* a retry loop, in dedicated migration / setup code, is not the target.

**Problem**: DDL operations are not transactional and not modeled by the retry classifier the same way DML errors are. `RetryQuerySync`'s `GetNextStep` reacts to `ABORTED`, `UNAVAILABLE`, `BAD_SESSION` etc. with assumptions about transactional rollback / session-reset semantics that don't hold for schema changes. A retried `CREATE TABLE` on `BAD_SESSION` can land twice; a retried `ALTER TABLE` mid-failure leaves the schema in a partially-applied state; co-locating DDL with DML in the same lambda binds the retry behaviour of both to the worst case of either.

**Fix**: run schema-creation / migration steps in dedicated, idempotent setup code outside the SDK retrier — typically a startup-time bootstrap that uses `ExecuteSchemeQuery` directly and reasons about its own failure mode. Keep `RetryQuerySync` / `RetryOperationSync` lambdas DML-only. If runtime-issued DDL is unavoidable, give it its own bounded retry strategy rather than reusing the query-retry classifier.

**Source**: YDB docs — error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling> and retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> (both frame the SDK retrier around DML status codes and transaction semantics, not schema-change semantics); status-code classification at <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes>. C++ DDL surface (`ExecuteSchemeQuery`, `CreateTable`) is declared in `include/ydb-cpp-sdk/client/table/table.h` of `ydb-platform/ydb-cpp-sdk`.
