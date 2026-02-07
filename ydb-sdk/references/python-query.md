# Python Query & Transactions (ydb) — Query/Table Service, Transactions

## Correct Usage Cheat Sheet

```python
# Query with retry (Query Service - preferred)
pool = ydb.QuerySessionPool(driver)
pool.execute_with_retries(
    "SELECT id, name FROM users WHERE id = $id",
    {"$id": user_id},
)

# Transaction with retry
def tx_operation(tx):
    tx.execute("UPDATE users SET name = $name WHERE id = $id", {"$name": name, "$id": user_id})
    tx.execute(
        "INSERT INTO logs (user_id, action) VALUES ($id, 'updated')",
        {"$id": user_id},
        commit_tx=True,  # commit with last query
    )

pool.retry_tx_operation(tx_operation)
```

---

## Query Rules

### RULE-Q03: SQL injection via f-strings
**Severity**: Critical

**What to look for**: `f"SELECT ... {var}"`, `"SELECT ... " + variable`, `.format()` in query text.

```python
# BAD
query = f"SELECT * FROM users WHERE login = '{user_login}'"
pool.execute_with_retries(query)

# GOOD
pool.execute_with_retries(
    "SELECT * FROM users WHERE login = $login",
    {"$login": user_login},
)
```

### RULE-Q06: Expecting >1000 rows from Table Service
**Severity**: High

**What to look for**: `session.transaction().execute()` (Table Service) for queries that may return >1000 rows.

```python
# BAD: Table Service — 1000 row limit
with driver.table_client.session().create() as session:
    result = session.transaction().execute(
        "SELECT * FROM events ORDER BY ts", commit_tx=True)
    # result_sets[0].rows — max 1000 rows

# GOOD: Query Service pool — no row limit
pool = ydb.QuerySessionPool(driver)
pool.execute_with_retries("SELECT * FROM events ORDER BY ts")
```

### RULE-Q10: Non-parametrized queries
**Severity**: High

**What to look for**: `f"..."`, `.format()`, `%` formatting in query strings, values inlined in query text.

```python
# BAD
query = f"SELECT * FROM users WHERE id = {user_id} AND status = '{status}'"

# GOOD
pool.execute_with_retries(
    "SELECT * FROM users WHERE id = $userId AND status = $status",
    {"$userId": user_id, "$status": status},
)
```

### RULE-Q12: Multiple sequential queries instead of batch
**Severity**: Medium

**What to look for**: Multiple separate `execute_with_retries()` calls that could be one multi-statement query.

```python
# BAD: three round-trips
pool.execute_with_retries("SELECT name FROM users WHERE user_id = $userId", {"$userId": user_id})
pool.execute_with_retries("SELECT title FROM products WHERE product_id = $productId", {"$productId": product_id})
pool.execute_with_retries("INSERT INTO orders ...", {...})

# GOOD: one round-trip
pool.execute_with_retries("""
    SELECT name FROM users WHERE user_id = $userId;
    SELECT title FROM products WHERE product_id = $productId;
    INSERT INTO orders ... RETURNING *;
""", {"$userId": user_id, "$productId": product_id, ...})
```

### RULE-Q13: KeepInCache not set in Table Service
**Severity**: Medium

**What to look for**: `session.transaction().execute()` without `settings=ydb.ExecDataQuerySettings().with_keep_in_cache(True)`.

```python
# BAD: Table Service without KeepInCache
session.transaction().execute(
    "SELECT * FROM users WHERE id = $id", {"$id": user_id})

# GOOD: with KeepInCache
session.transaction().execute(
    "SELECT * FROM users WHERE id = $id", {"$id": user_id},
    settings=ydb.ExecDataQuerySettings().with_keep_in_cache(True))

# BEST: Query Service (caching by default)
pool.execute_with_retries("SELECT * FROM users WHERE id = $id", {"$id": user_id})
```

---

## Transaction Rules

### RULE-TX01: Explicit BeginTx (extra round-trip)
**Severity**: Medium

**What to look for**: `tx.begin()`, explicit `session.transaction()` with `begin()` call.

```python
# BAD
tx = session.transaction()
tx.begin()
result = tx.execute("SELECT * FROM users WHERE id = $id", {"$id": 123})
tx.commit()

# GOOD: auto-begin with first query
result = session.execute(
    "SELECT * FROM users WHERE id = $id",
    {"$id": 123},
    commit_tx=True,
)
```

### RULE-TX02: Separate Commit (extra round-trip)
**Severity**: Medium

**What to look for**: `tx.commit()` as a separate call after last query.

```python
# BAD: explicit commit
tx.execute("UPDATE users SET status = 'active' WHERE id = $id", {"$id": user_id})
tx.execute("INSERT INTO logs ...", {"$id": user_id})
tx.commit()  # extra round-trip

# GOOD: commit with last query
tx.execute("UPDATE users SET status = 'active' WHERE id = $id", {"$id": user_id})
tx.execute("INSERT INTO logs ...", {"$id": user_id}, commit_tx=True)
```
