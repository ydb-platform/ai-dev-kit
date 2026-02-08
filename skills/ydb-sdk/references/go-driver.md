# Go Driver (ydb-go-sdk) — Connection, Balancer, Sessions, Retry

## SDK Detection
- Import: `github.com/ydb-platform/ydb-go-sdk`
- Go module: `github.com/ydb-platform/ydb-go-sdk/v3`

## Correct Usage Cheat Sheet

```go
// Driver initialization
db, err := ydb.Open(ctx, "grpcs://endpoint:2135/database",
    ydb.WithBalancer(balancers.RandomChoice()),
)
defer db.Close(ctx)

// Simple query with retry
err = db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    res, err := s.Query(ctx,
        `SELECT id, name FROM users WHERE id = $id`,
        query.WithParameters(ydb.ParamsBuilder().Param("$id").Uint64(userID).Build()),
    )
    if err != nil { return err }
    defer res.Close(ctx)
    // ... read results inside lambda ...
    return nil
}, query.WithIdempotent())
```

---

## Balancer Rules

### RULE-B01: PreferLocalDC creates hot spots
**Severity**: High

**What to look for**: `balancers.PreferLocalDC`, `balancers.PreferNearestDC`

```go
// BAD
db, err := ydb.Open(ctx, connectionString,
    ydb.WithBalancer(balancers.PreferLocalDC(balancers.RandomChoice())),
)

// GOOD
db, err := ydb.Open(ctx, connectionString,
    ydb.WithBalancer(balancers.RandomChoice()),
)
```

### RULE-B02: Not handling BAD_SESSION (manual session management)
**Severity**: Medium

**What to look for**: `db.Table().CreateSession(ctx)`, direct session creation and reuse, `session.Execute()` without `Do()` wrapper.

```go
// BAD: manual session management
session, err := db.Table().CreateSession(ctx)
result, err := session.Execute(ctx, query)

// GOOD: use session pool via Do()
err := db.Table().Do(ctx, func(ctx context.Context, s table.Session) error {
    _, err := s.Execute(ctx, query)
    return err
}, table.WithIdempotent())
```

---

## Retry Rules

### RULE-R01: No retry logic at all
**Severity**: Critical

**What to look for**: Direct `session.Execute()`, `session.Query()` without `Do()` / `DoTx()` wrapper.

```go
// BAD
res, err := session.Execute(ctx, "SELECT 1")

// GOOD
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    res, err := s.Query(ctx, "SELECT 1")
    return err
}, query.WithIdempotent())
```

### RULE-R02: Custom retrier instead of SDK
**Severity**: High

**What to look for**: `for` loops with `time.Sleep` wrapping YDB calls.

```go
// BAD
func badRetry(fn func() error) error {
    for i := 0; i < 10; i++ {
        if err := fn(); err == nil { return nil }
        time.Sleep(100 * time.Millisecond)
    }
    return errors.New("max retries")
}

// GOOD
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    _, err := s.Query(ctx, `SELECT 42`)
    return err
}, query.WithIdempotent())
```

### RULE-R03: Retrying all errors (wrapping Do in a loop)
**Severity**: High

**What to look for**: `for { ... db.Query().Do(...) ... }` — infinite retry around `Do()`.

```go
// BAD: infinite retry around Do()
for {
    err := driver.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        return nil
    })
    if err == nil { break }
    time.Sleep(time.Second)
}

// GOOD: Do() already handles retries
err := driver.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    return nil
})
```

### RULE-R04: Leaking temporary objects out of retry closure
**Severity**: High

**What to look for**: Variables declared outside `Do()` lambda that capture `result.Result`, response objects, or iterators.

```go
// BAD: result leaks out of lambda
var res result.Result
err := db.Table().Do(ctx, func(ctx context.Context, s table.Session) (err error) {
    res, err = s.Execute(ctx, `SELECT * FROM bigTable;`)
    return err
})
// res may be from a failed attempt!

// GOOD: process inside, assign final value
var myObjs []MyObject
err := db.Table().Do(ctx, func(ctx context.Context, s table.Session) (err error) {
    myObjs = nil // clear on each attempt
    res, err := s.Execute(ctx, `SELECT * FROM bigTable;`)
    if err != nil { return err }
    // scan into myObjs inside lambda
    return nil
})
```

### RULE-R05: No cleanup between retry attempts
**Severity**: High

**What to look for**: `append()` to external slice inside `Do()` lambda without clearing first.

```go
// BAD: duplicates on retry
var results []string
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    results = append(results, titles...) // duplicates on retry!
    return nil
})

// GOOD: clear at start
var results []string
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    var attemptResults []string
    // ... scan into attemptResults ...
    results = attemptResults // replace only on success
    return nil
})
```

### RULE-R06: Full stream retry instead of pagination
**Severity**: Medium

**What to look for**: `SELECT * FROM large_table` without LIMIT/OFFSET, streaming without checkpoints.

```go
// BAD
rows, err := db.Query("SELECT * FROM large_table")

// GOOD: paginated reads
var lastKey uint64
for {
    err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        res, err := s.Query(ctx,
            `SELECT id, data FROM large_table WHERE id > $lastKey ORDER BY id LIMIT 1000`,
            query.WithParameters(ydb.ParamsBuilder().Param("$lastKey").Uint64(lastKey).Build()),
        )
        // ... process batch, update lastKey ...
        return nil
    }, query.WithIdempotent())
}
```

### RULE-R07: Missing idempotency flag
**Severity**: High

**What to look for**: `Do()`, `DoTx()`, `retry.Do()` without `WithIdempotent()` / `query.WithIdempotent()` for read or UPSERT operations.

```go
// BAD: idempotent SELECT without flag
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    return executeSelectQuery(ctx, s)
})

// GOOD
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    return executeSelectQuery(ctx, s)
}, query.WithIdempotent())
```

### RULE-R08: Nested retry calls (deadlock)
**Severity**: Critical

**What to look for**: `db.Query().Do()` inside another `Do()` lambda. Any retrier inside a retrier.

```go
// BAD: deadlock risk
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    return db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        return nil
    })
})

// GOOD: pass session through call chain
err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
    return helperFunction(ctx, s) // use s directly
})
```

---

## Testing

### RULE-C02: Not testing with real YDB
**Severity**: Low

**What to look for**: Tests with only mocks/stubs for YDB, no integration tests.

**Fix**: Use YDB Docker container (`ydbplatform/local-ydb:latest`) for integration tests.
