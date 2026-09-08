# Embedding YDB in Python applications

Scope: query execution and large reads. Transactions beyond the shapes below, topics, and coordination are not covered here yet — for those, point at <https://ydb-platform.github.io/ydb-python-sdk> rather than generalizing.

## Stack

The official SDK is **`ydb`** (<https://github.com/ydb-platform/ydb-python-sdk>), Python 3.10+. One package exposes both surfaces:

- the **Query Service** (preferred for new code) — `ydb.QuerySessionPool`, `ydb.aio.QuerySessionPool`,
- the legacy **Table Service** — `driver.table_client`, `ydb.SessionPool`, `session.transaction().execute(...)`.

Connection strings and authentication environment variables: [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting). Worked examples: <https://github.com/ydb-platform/ydb-python-sdk/tree/master/examples>.

## Query execution

Open the driver once per process, build one pool on top of it, and run queries through the pool. The pool owns retries.

```python
import ydb

driver = ydb.Driver(ydb.DriverConfig(endpoint="grpc://localhost:2136", database="/local"))
driver.wait(timeout=5, fail_fast=True)

pool = ydb.QuerySessionPool(driver)

result_sets = pool.execute_with_retries(
    "SELECT name FROM users WHERE id = $id;",
    parameters={"$id": (42, ydb.PrimitiveType.Uint64)},
)
for result_set in result_sets:
    for row in result_set.rows:
        ...
```

Two load-bearing pieces:

- **`parameters=` binds values.** Pass either an implicitly typed value (`{"$id": 42}`) or an explicit `(value, ydb_type)` pair when the inferred type would be wrong. Never concatenate values into the query text — that defeats plan-cache reuse and opens injection.
- **`execute_with_retries` is the retry unit.** It acquires a session, runs the query, and replays on retryable errors. Do not write your own `for attempt in range(...)` loop around it.

Source: <https://github.com/ydb-platform/ydb-python-sdk/blob/master/examples/query-service/basic_example.py>.

## Reading a large result set

`execute_with_retries` is the wrong call for an unbounded read. Its own docstring is explicit: *"this method loads all data from stream before return, do not use this method with huge read queries."* It aggregates every result set into a list before returning, so the peak memory is the size of the match.

For a read whose size is not bounded by construction, keep the stream and consume it inside the retried callable:

```python
def read_all(session):
    total = 0
    with session.execute("SELECT id, payload FROM events;") as result_sets:
        for result_set in result_sets:
            for row in result_set.rows:
                total += handle(row)
    return total

total = pool.retry_operation_sync(read_all)
```

`session.execute(...)` returns a streaming iterator over result sets, so client-side memory stays bounded by one part rather than the whole match. The callable is the retry unit: a transient failure replays it from the top, so side effects inside it must be idempotent per key, and values must be assigned to outer names only on the success path.

Streaming still replays the whole read on a mid-stream failure. When the match is large enough that re-reading it is unacceptable, cut it into keyset-paginated batches so each batch is its own retry scope — the YDB-level recipe, its tuple-order and `OFFSET` caveats, live in [`../working-with-data.md`](../working-with-data.md) under "Reading many rows".

```python
cursor = 0
batch = 1000
while True:
    page = pool.execute_with_retries(
        """
        SELECT id, payload FROM events
        WHERE id > $cursor
        ORDER BY id
        LIMIT $batch;
        """,
        parameters={
            "$cursor": (cursor, ydb.PrimitiveType.Uint64),
            "$batch": (batch, ydb.PrimitiveType.Uint64),
        },
    )
    rows = page[0].rows if page else []
    if not rows:
        break
    for row in rows:
        handle(row)
    cursor = rows[-1].id
    if len(rows) < batch:
        break
```

Here `execute_with_retries` is correct because each page is bounded by `$batch`. The cursor lives in process memory; persist it externally to resume across restarts — the SDK has no checkpoint API.

## Migrating off `scan_query`

`driver.table_client.scan_query(...)`, its `async_scan_query` sibling, and the `ydb.aio` table client's `scan_query` are the legacy Table Service scan interface. Scan queries are deprecated — see [`../working-with-data.md`](../working-with-data.md) for what they cost at the YDB level.

| Legacy call | Replacement |
| --- | --- |
| `driver.table_client.scan_query(q)` iterated for its rows | `pool.retry_operation_sync(...)` around `session.execute(q)`, per "Reading a large result set" above |
| `scan_query` used to dodge the Table Service row cap | Query Service streaming — it has no such cap, so no workaround is needed |
| `scan_query` over an unbounded range | Query Service plus keyset pagination |
| `driver.table_client.async_scan_query(q)` | `ydb.aio.QuerySessionPool` with `retry_operation_async` / `execute_with_retries_async` |

The rewrite is not a one-line substitution: `scan_query` returns an iterator, so swapping it for `execute_with_retries` silently converts a streaming read into a fully buffered one. Match streaming with streaming.

Scan queries also carried no SDK-side retries, so migrated code often has a hand-rolled retry loop wrapped around the old call. Delete it — `retry_operation_sync` and `execute_with_retries` already retry.

## Async

`ydb.aio.Driver` and `ydb.aio.QuerySessionPool` mirror the sync API: `await pool.execute_with_retries(...)`, `await pool.retry_operation_async(callee)`, and `async with await session.execute(...) as result_sets:` for streaming — note the inner `await`, the call returns an awaitable that yields the async context manager. The same buffering caveat applies to `execute_with_retries_async`.

Source: <https://github.com/ydb-platform/ydb-python-sdk/blob/master/examples/query-service/basic_example_asyncio.py>.

## Connection

See [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting).
