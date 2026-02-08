# Python Driver (ydb) — Connection, Retry, Configuration

## SDK Detection
- Import: `import ydb`, `from ydb import ...`
- Package: `ydb` (PyPI)

## Correct Usage Cheat Sheet

```python
import ydb
import os

# Driver initialization
driver = ydb.Driver(
    endpoint=os.getenv("YDB_ENDPOINT"),
    database=os.getenv("YDB_DATABASE"),
    credentials=ydb.credentials_from_env_variables(),
)
driver.wait(timeout=5)

# Query with retry (Query Service - preferred)
pool = ydb.QuerySessionPool(driver)
pool.execute_with_retries(
    "SELECT id, name FROM users WHERE id = $id",
    {"$id": user_id},
)
```

---

## Retry Rules

### RULE-R01: No retry logic at all
**Severity**: Critical

**What to look for**: Direct `session.transaction().execute()`, `session.execute()` without pool retry wrapper.

```python
# BAD
session.transaction().execute("SELECT 1")

# GOOD
pool.execute_with_retries("SELECT 1")
```

### RULE-R02: Custom retrier instead of SDK
**Severity**: High

**What to look for**: `for i in range(...)` or `while True` loops with `time.sleep()` wrapping YDB calls.

```python
# BAD
def bad_retry(func, max_attempts=10):
    for i in range(max_attempts):
        try: return func()
        except: time.sleep(0.1)

# GOOD
pool.execute_with_retries(query, params)
```

### RULE-R07: Missing idempotency flag
**Severity**: High

**What to look for**: `execute_with_retries()` without `RetrySettings(idempotent=True)` for read or UPSERT operations.

```python
# BAD
pool.execute_with_retries(query)

# GOOD
pool.execute_with_retries(
    query, params,
    retry_settings=ydb.RetrySettings(idempotent=True),
)
```

---

## Configuration Rules

### RULE-C01: Aggressive gRPC keep-alive
**Severity**: Medium

**What to look for**: `grpc_keep_alive_timeout` < 10000 in `DriverConfig`.

```python
# BAD
driver_config = ydb.DriverConfig(
    endpoint=..., database=...,
    grpc_keep_alive_timeout=1000,  # 1 second — too aggressive
)

# GOOD: use defaults (10 seconds)
driver_config = ydb.DriverConfig(
    endpoint=..., database=...,
    # grpc_keep_alive_timeout=10000  # default is fine
)
```
