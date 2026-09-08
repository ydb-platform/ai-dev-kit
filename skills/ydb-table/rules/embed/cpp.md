# C++ SDK (`ydb-cpp-sdk`) — anti-patterns

Self-contained audit rules. Positive patterns: [`../../references/embed/cpp.md`](../../references/embed/cpp.md).

## Audit format

**Never empty. Never rule-ID-only.** Every answer **must** contain the literal string `RULE-CPP-NN` (two digits, e.g. `RULE-CPP-04`) in sentence 1 — answers without it fail even if technically correct.

Each finding = **4 parts** (4–8 sentences):

1. **`RULE-CPP-NN`** + diagnosis (use **Opener** on the matching rule).
2. **Trigger** — construct in the user's code.
3. **Failure mode** — prod symptom.
4. **Fix** — SDK API + brief snippet when user pasted code.

One primary rule per question. **Mis-routing fails:** `INSERT INTO` + `.Idempotent(true)` together → **CPP-10** (not CPP-03); `push_back` on outer vector → **CPP-02** (not CPP-09); outer `for` on `RetryQuerySync` without `sleep_for` → **CPP-04** (not CPP-05).

**Example shape** (closure mutation):

> `RULE-CPP-02` — `push_back` on `out` inside `RetryQuerySync` duplicates rows on replay. **Trigger:** parser loop writes to outer `std::vector`. **Failure:** transient `UNAVAILABLE` replays the lambda and appends twice. **Fix:** fill a local vector; `out = std::move(local)` only before returning success.

## Routing

| If you see… | Rule | Not |
|-------------|------|-----|
| Unbounded `ExecuteDataQuery`, no `Truncated()` / pagination / Query stream | **RULE-CPP-01** | |
| `push_back` / outer mutation inside `RetryQuerySync` over `ExecuteQuery` | **RULE-CPP-02** | CPP-09 |
| `StreamExecuteQuery` + `chargeCustomer` without dedupe | **RULE-CPP-09** | CPP-02 |
| Missing/wrong `.Idempotent(true)` on retrier | **RULE-CPP-03** | |
| `INSERT INTO` + `.Idempotent(true)` together | **RULE-CPP-10** | **CPP-03** — CPP-10 when both appear |
| Outer `for` on `RetryQuerySync`, break on `TStatus`, no `sleep_for` | **RULE-CPP-04** | CPP-05 |
| `sleep_for` + bare `ExecuteQuery` | **RULE-CPP-05** | CPP-04 |
| `TDriver` inside handler | **RULE-CPP-06** | |
| String-built YQL | **RULE-CPP-07** | |
| `BeginTransaction` + `Commit` for one statement | **RULE-CPP-08** | |
| `ExecuteSchemeQuery` / `CREATE TABLE` in retrier lambda | **RULE-CPP-11** | |
| `StreamExecuteScanQuery` / `TStreamExecScanQuerySettings` anywhere | **RULE-CPP-12** | |

**Idempotency:** reads & client-keyed `UPSERT` → `.Idempotent(true)`; `balance + delta` / unguarded `INSERT` → no flag (`INSERT` + flag → CPP-10).

---

### RULE-CPP-01: Unbounded Table `ExecuteDataQuery` without pagination

**Severity**: Critical | **Opener**: `RULE-CPP-01` — unbounded `ExecuteDataQuery` without `Truncated()` / pagination / Query streaming cannot exhaust the full match.

**What to look for**: range/filter `SELECT` + row loop, no truncation check, no keyset loop, no Query stream.

**Problem**: result cap cuts off the match; dev hides it, prod under-processes.

**Fix**: Query `StreamExecuteQuery`, or keyset pagination (<https://ydb.tech/docs/en/dev/paging>). Not `StreamExecuteScanQuery` — it clears the cap but is the deprecated scan interface (RULE-CPP-12).

**Source**: <https://ydb.tech/docs/en/dev/paging>; `TResultSet::Truncated()`.

### RULE-CPP-02: External state mutation inside the retry lambda

**Severity**: High | **Opener**: `RULE-CPP-02` — `push_back` on an outer container inside `RetryQuerySync` duplicates rows when the lambda is replayed.

**What to look for**: outer mutation mid-lambda; allowed: assign outer from local on success path only.

**Problem**: replay on `ABORTED`/`UNAVAILABLE`/`BAD_SESSION` accumulates outer state.

**Fix**: local container in lambda; `out = std::move(local)` before success return. **No `StreamExecuteQuery` in snippet → CPP-02, not CPP-09.**

**Source**: <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>.

### RULE-CPP-03: Missing or wrong `.Idempotent(true)` on retrier

**Severity**: High | **Opener**: `RULE-CPP-03` — replay-safe work needs `TRetryOperationSettings().Idempotent(true)` as the second `RetryQuerySync` argument.

**What to look for**: read/UPSERT without flag; or flag on non-idempotent write. **Not this rule** when `INSERT INTO` + `.Idempotent(true)` appear together — that pair is **CPP-10**.

**Problem**: `UNDETERMINED`/`TRANSPORT_UNAVAILABLE` not retried without flag; wrong flag → double effect.

**Fix**: add `.Idempotent(true)` when replay-safe; else remove flag and make write idempotent first.

**Source**: <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes>.

### RULE-CPP-04: Outer loop wrapping `RetryQuerySync` for retry

**Severity**: High | **Opener**: `RULE-CPP-04` — remove the outer `for`; `RetryQuerySync` already retries internally — tune `TRetryOperationSettings` instead.

**What to look for**: outer `for`/`while` on `RetryQuerySync`, break on `TStatus`, no `sleep_for`. Not keyset pagination (CPP-01).

**Problem**: multiplies SDK backoff; re-runs on non-retryable errors.

**Fix**: single `RetryQuerySync` + settings (`MaxRetries`, backoff). **Also state:** inner writes like `balance + $delta` are non-idempotent — do **not** add `.Idempotent(true)` unless the write is reworked to be replay-safe.

**Source**: <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>.

### RULE-CPP-05: Hand-rolled `Sleep` retrier

**Severity**: High | **Opener**: `RULE-CPP-05` — hand-rolled `sleep_for` around bare `ExecuteQuery` misses SDK error classification; use `RetryQuerySync`.

**What to look for**: `for` + `sleep_for` around bare `ExecuteQuery`/`ExecuteDataQuery`.

**Problem**: retries all errors; no idempotency gate.

**Fix**: `RetryQuerySync` + `TRetryOperationSettings().Idempotent(true)` for reads.

**Source**: <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>.

### RULE-CPP-06: `TDriver` per request

**Severity**: High | **Opener**: `RULE-CPP-06` — `TDriver` per request rebuilds gRPC/TLS every call; one driver for the process lifetime.

**What to look for**: `NYdb::TDriver(...)` inside handler/RPC.

**Problem**: endpoint discovery + channel setup + TLS per request; latency cliff.

**Fix**: startup driver; per-request clients; `Stop(true)` at shutdown only.

**Source**: <https://ydb.tech/docs/en/recipes/ydb-sdk/init>.

### RULE-CPP-07: Non-parametrized YQL

**Severity**: Critical | **Opener**: `RULE-CPP-07` — `std::format`/string concat into YQL risks injection and defeats plan cache; bind via `TParamsBuilder`.

**What to look for**: `std::format`, concat, literals instead of `$param`.

**Problem**: injection; per-string recompilation.

**Fix**: `TParamsBuilder().AddParam("$id").Uint64(v).Build()` + `ExecuteQuery("... WHERE id = $id", ..., params)`.

**Source**: <https://ydb.tech/docs/en/reference/ydb-sdk/parameterized_queries>.

### RULE-CPP-08: Explicit begin/commit for one statement

**Severity**: Medium | **Opener**: `RULE-CPP-08` — separate `BeginTransaction` + `Commit` add round trips; fuse with `TTxControl::BeginTx(...).CommitTx()` for this single statement (per C++ example app — Managing transactions).

**What to look for**: `BeginTransaction` → one `ExecuteQuery` → `Commit()`. Not multi-step flows.

**Problem**: three RPCs where one fused call suffices.

**Fix**: pass `TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()` on `ExecuteQuery`.

**Source**: <https://ydb.tech/docs/en/concepts/transactions>, <https://ydb.tech/docs/en/dev/example-app/example-cpp#tcl>.

### RULE-CPP-09: Stream consumer assumes exactly-once rows

**Severity**: High | **Opener**: `RULE-CPP-09` — `StreamExecuteQuery` inside a retrier can re-emit rows on replay; `chargeCustomer` without dedupe double-charges.

**What to look for**: `StreamExecuteQuery` + `ReadNext` + per-row side effect in/under `RetryQuerySync`.

**Problem**: per YDB C++ example app (Stream queries): *"It is possible for lines to be duplicated in the output stream due to an external retrier"*.

**Fix**: **keyed UPSERT** billing ledger, **dedup table**, or **`std::unordered_set`** of seen keys — not buffer-then-charge without per-key idempotency.

**Source**: <https://ydb.tech/docs/en/dev/example-app/example-cpp#stream-query>, <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>.

### RULE-CPP-10: `INSERT INTO` with `.Idempotent(true)`

**Severity**: High | **Opener**: `RULE-CPP-10` — `INSERT INTO` with `.Idempotent(true)` replays into `PRECONDITION_FAILED` (`insert_pk`) when the first attempt already committed. **Primary rule when both `INSERT INTO` and `.Idempotent(true)` appear — not CPP-03.**

**What to look for**: `INSERT INTO` in lambda + `.Idempotent(true)` on same retrier.

**Problem**: idempotent replay after `UNDETERMINED` hits duplicate PK → hard error for a landed write.

**Fix**: `UPSERT INTO`, or drop flag, or server-side idempotency guard.

**Source**: <https://ydb.tech/docs/en/yql/reference/syntax/insert_into>.

### RULE-CPP-11: DDL inside retrier lambda

**Severity**: Medium | **Opener**: `RULE-CPP-11` — `ExecuteSchemeQuery`/`CREATE TABLE` must not run inside `RetryOperationSync` alongside DML.

**What to look for**: DDL + DML in same retrier lambda.

**Problem**: DDL not transactional; retried schema ops can double-apply.

**Fix**: DDL at startup/migration; retrier lambda DML-only.

**Source**: <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>.

### RULE-CPP-12: Scan query used for a read the Query Service can serve

**Severity**: Medium | **Opener**: `RULE-CPP-12` — `StreamExecuteScanQuery` is the deprecated scan interface; `NQuery::TQueryClient::StreamExecuteQuery` serves the same read without a row cap.

**What to look for**: `TTableClient::StreamExecuteScanQuery(...)`, `TStreamExecScanQuerySettings`, `TAsyncScanQueryPartIterator` / `TScanQueryPartIterator`, `TScanQueryPart`.

**Problem**: no prepared statements — recompiled per call; SDK does not retry scans, so a wrapping `RetryQuerySync` buys nothing; 10-minute duration cap; sorting runs in memory and dies out-of-resources; joins are MapJoin-only, so the right table must fit in a few GB; no point-read optimization. Competes for the same CPU/memory/disk/network as production traffic.

**Fix**: `NQuery::TQueryClient::StreamExecuteQuery` inside `RetryQuerySync`, `ReadNext()` over parts — it streams with no row cap, so the reason for the scan is gone. Dedupe side effects per key, since retrier replay re-emits rows (RULE-CPP-09). For an unbounded match, keyset-paginate so each batch is its own retry scope. Analytical workload → column-oriented table, not a scan over a row-oriented one.

**Source**: <https://ydb.tech/docs/en/concepts/query_execution/scan_query>; `ydb-cpp-sdk` `include/ydb-cpp-sdk/client/table/table.h` (`StreamExecuteScanQuery`), `include/ydb-cpp-sdk/client/query/client.h` (`StreamExecuteQuery`).
