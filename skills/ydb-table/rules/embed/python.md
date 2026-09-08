# Python SDK (`ydb`) — anti-patterns

Audit rules for application code talking to YDB through the Python SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own.

### RULE-PY-01: Scan query used for a read the Query Service can serve

**Severity**: Medium

**What to look for**: `driver.table_client.scan_query(...)`, `driver.table_client.async_scan_query(...)`, `scan_query(...)` on an `ydb.aio` table client, construction of `ydb.ScanQuery(...)`, or a `ydb.ScanQuerySettings` object passed into one of those calls. Any of these in new code, or in code being modified, is the target. A read that already goes through `ydb.QuerySessionPool` is not.

**Problem**: scan queries are the deprecated Table Service analytics interface — upstream marks the functionality deprecated and directs new code at standard query execution. They look attractive because they stream over gRPC with no row-count cap, but they carry costs the Query Service does not: prepared statements are unsupported, so the query is compiled on every call; the SDK does not retry them automatically, so a transient failure surfaces raw to the caller; query duration is capped at 10 minutes; sorting and other operations run entirely in memory and fail with out-of-resources on complex queries; joins support only the MapJoin strategy, so the right-hand table must fit in a few gigabytes; and there are no optimizations for point or small-range reads. A scan also competes for the same CPU, memory, disk and network as production traffic, so a heavy one can starve the whole database.

**Fix**: run the read through `ydb.QuerySessionPool` instead. For a bounded read, `pool.execute_with_retries(query, parameters={...})`. For an unbounded read, keep it streaming — `pool.retry_operation_sync(callee)` where the callable consumes `with session.execute(query) as result_sets:` — because `execute_with_retries` buffers the whole match before returning. When re-reading the match on a mid-stream failure is unacceptable, keyset-paginate over the primary key so each batch is its own retry scope. Async code uses `ydb.aio.QuerySessionPool` with `retry_operation_async` / `execute_with_retries_async`. Delete any hand-rolled retry loop that existed only because scan queries were not retried by the SDK.

**Source**: <https://ydb.tech/docs/en/concepts/query_execution/scan_query>; `ydb/query/pool.py` — `QuerySessionPool.execute_with_retries`, `QuerySessionPool.retry_operation_sync`.

### RULE-PY-02: `execute_with_retries` used for an unbounded read

**Severity**: High

**What to look for**: `pool.execute_with_retries(...)` or `await pool.execute_with_retries_async(...)` whose query has no `LIMIT` and no key-ranged `WHERE` — an unfiltered `SELECT`, a `WHERE status = 'pending'` over an unbounded set, a `WHERE created_at > $cutoff` range — especially where the result is then iterated to process the full match. A query bounded by `LIMIT $batch` inside a keyset loop is not the target. This rule fires most often on code freshly migrated off `scan_query`, where a streaming call was swapped for a buffering one.

**Problem**: `execute_with_retries` aggregates every result set from the stream into a list before it returns — its docstring says so outright: *"this method loads all data from stream before return, do not use this method with huge read queries."* Peak client memory is therefore the size of the whole match, not of one stream part. The call works on a dev dataset and dies with the process on production data; the failure is data-dependent, so tests on small fixtures never surface it.

**Fix**: consume the stream instead of materializing it — `pool.retry_operation_sync(callee)` with `with session.execute(query, parameters) as result_sets:` inside the callable, iterating result sets and rows as they arrive. Keep values assigned to outer names only on the callable's success path, since the callable is replayed on retry. If the read must survive mid-stream failures without re-reading everything, keyset-paginate over the primary key and keep `execute_with_retries` for the individual bounded pages.

**Source**: `ydb/query/pool.py` — `QuerySessionPool.execute_with_retries` docstring and its `convert.aggregate_result_sets_by_index` call.
