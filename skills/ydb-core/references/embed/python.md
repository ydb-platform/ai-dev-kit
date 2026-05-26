# Balancing and sessions in Python (`ydb`)

Principles: [`../balancing.md`](../balancing.md), [`../session-lifecycle.md`](../session-lifecycle.md).

## Default balancer

```python
import ydb

with ydb.Driver(
    endpoint=os.environ["YDB_ENDPOINT"],
    database=os.environ["YDB_DATABASE"],
    credentials=ydb.credentials_from_env_variables(),
) as driver:
    driver.wait(timeout=5)
```

`use_all_nodes` defaults to `True` on `ydb.Driver(...)` (`ydb-python-sdk/ydb/driver.py: use_all_nodes: bool = True`). Equivalent of Go's `balancers.RandomChoice()`.

## Anti-pattern: `use_all_nodes=False`

```python
ydb.Driver(
    endpoint=endpoint, database=database,
    use_all_nodes=False,             # ← prefer-DC behavior
    credentials=...,
)
```

Conn-list ordering switches to `(preferred, connections)` (`ydb-python-sdk/ydb/pool.py: ConnectionsCache`). Same failure modes as Go's `PreferLocalDC`. Justified only with followers + `StaleRO`.

## Sessions

Use the session-pool helpers (`session_pool.execute_with_retries(...)`, query-service equivalents on `driver.query`). Do not store a `Session` in an attribute and reuse across calls.

## Sources

- `ydb-python-sdk/ydb/driver.py`
- `ydb-python-sdk/ydb/pool.py`
