# Go Query & Transactions (ydb-go-sdk) — Query/Table Service, Transactions

## Correct Usage Cheat Sheet

```go
// Query with retry (Query Service - preferred)
err = db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    res, err := s.Query(ctx,
        `SELECT id, name FROM users WHERE id = $id`,
        query.WithParameters(ydb.ParamsBuilder().Param("$id").Uint64(userID).Build()),
    )
    if err != nil { return err }
    defer res.Close(ctx)
    return nil
}, query.WithIdempotent())

// Transaction with retry
err = db.Query().DoTx(ctx, func(ctx context.Context, tx query.TxActor) error {
    _, err := tx.Exec(ctx, `UPDATE users SET name = $name WHERE id = $id`,
        query.WithParameters(...),
    )
    if err != nil { return err }
    _, err = tx.Exec(ctx, `INSERT INTO logs ...`,
        query.WithCommit(), // commit with last query
    )
    return err
}, query.WithIdempotent())
```

---

## Query Rules

### RULE-Q03: SQL injection via string formatting
**Severity**: Critical

**What to look for**: `fmt.Sprintf` with query text, string concatenation in queries, `"SELECT ... " + variable`.

```go
// BAD
query := fmt.Sprintf("SELECT * FROM users WHERE id = %d", userID)

// GOOD
db.Query().Query(ctx,
    `SELECT * FROM users WHERE id = $id`,
    query.WithParameters(ydb.ParamsBuilder().Param("$id").Uint64(userID).Build()),
)
```

### RULE-Q05: Using deprecated Scripting Service
**Severity**: Medium

**What to look for**: `db.Scripting()`, import `ydb-go-sdk/v3/scripting`.

```go
// BAD
res, err := db.Scripting().Execute(ctx, "SELECT * FROM series", table.NewQueryParameters())

// GOOD
result, err := db.Query().Query(ctx, "SELECT * FROM series")
```

### RULE-Q06: Expecting >1000 rows from Table Service
**Severity**: High

**What to look for**: `driver.Table().Do()` + `s.Execute()` for queries returning potentially >1000 rows.

```go
// BAD: Table Service — 1000 row limit
err := driver.Table().Do(ctx, func(ctx context.Context, s table.Session) error {
    result, err := s.Execute(ctx, table.DefaultTxControl(),
        "SELECT * FROM events ORDER BY ts", nil)
    return err
})

// GOOD: Query Service — no row limit
err := driver.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    result, err := s.QueryResultSet(ctx,
        "SELECT * FROM events ORDER BY ts", nil)
    return err
})
```

### RULE-Q10: Non-parametrized queries
**Severity**: High

**What to look for**: `fmt.Sprintf` building query strings, values inlined in query text.

```go
// BAD
query := fmt.Sprintf("SELECT * FROM users WHERE id = %d AND status = '%s'", userID, status)

// GOOD
db.Query().Query(ctx,
    `SELECT * FROM users WHERE id = $userId AND status = $status`,
    query.WithParameters(
        ydb.ParamsBuilder().
            Param("$userId").Uint64(userID).
            Param("$status").Text(status).
            Build(),
    ),
)
```

### RULE-Q11: Not checking plan after schema changes
**Severity**: Medium

**What to look for**: Schema ALTER/CREATE in code or migrations without plan verification tests.

**Fix**: Add tests that verify query plans for critical queries using `query.WithExecMode(query.ExecModeExplain)`.

### RULE-Q12: Multiple sequential queries instead of batch
**Severity**: Medium

**What to look for**: Multiple `s.Query()` / `tx.Exec()` calls in sequence that could be one multi-statement query.

```go
// BAD: three round-trips
db.Query().Query(ctx, `SELECT name FROM users WHERE user_id = $userId`, ...)
db.Query().Query(ctx, `SELECT title FROM products WHERE product_id = $productId`, ...)
db.Query().Query(ctx, `INSERT INTO orders ...`, ...)

// GOOD: one round-trip
db.Query().Query(ctx,
    `SELECT name FROM users WHERE user_id = $userId;
     SELECT title FROM products WHERE product_id = $productId;
     INSERT INTO orders ... RETURNING *;`,
    query.WithParameters(...),
)
```

### RULE-Q13: KeepInCache not set in Table Service
**Severity**: Medium

**What to look for**: `s.Execute()` in `db.Table().Do()` without `table.WithKeepInCache(true)` (only when using legacy Table Service).

**Fix**: Set `KeepInCache`, or better — migrate to Query Service where caching is on by default.

### RULE-Q17: Using Prepared Statements
**Severity**: Medium

**What to look for**: `session.Prepare()` + `session.Execute(queryId)`, stored statement IDs.

**Problem**: Prepared statements are tied to a session. Closed session = lost statement. Complex lifecycle management needed.

**Fix**: Use parametrized queries with KeepInCache (or Query Service).

---

## Transaction Rules

### RULE-TX01: Explicit BeginTx (extra round-trip)
**Severity**: Medium

**What to look for**: `session.BeginTransaction()`, `s.Begin()` calls.

```go
// BAD: explicit BeginTx
tx, err := session.BeginTransaction(ctx, table.TxSettings(table.WithSerializableReadWrite()))
res, err := tx.Execute(ctx, query)
err = tx.Commit(ctx)

// GOOD: begin with first query
res, err := session.Execute(ctx, query,
    table.WithTxControl(table.BeginTx(table.WithSerializableReadWrite()), table.CommitTx()),
)

// GOOD: LazyTx
db, err := ydb.Open(ctx, "grpc://localhost:2136/local", ydb.WithLazyTx(true))
err = db.Query().DoTx(ctx, func(ctx context.Context, tx query.TxActor) error {
    res, err := tx.Query(ctx, `SELECT 42`) // tx starts with first query
    return err
})
```

### RULE-TX02: Separate Commit (extra round-trip)
**Severity**: Medium

**What to look for**: `tx.Commit(ctx)` / `tx.CommitTx(ctx)` as a separate call after the last query.

```go
// BAD: separate commit
_, err = tx.Exec(ctx, lastQuery)
err = tx.CommitTx(ctx) // extra round-trip

// GOOD: commit with last query
_, err = tx.Exec(ctx, lastQuery, query.WithCommit())
```
