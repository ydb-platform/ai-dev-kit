# Go SDK (`ydb-go-sdk/v3`) — anti-patterns

Audit rules for application code talking to YDB through the Go SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own.

### RULE-GO-01: Reading "all matching rows" through Table Service without pagination

**Severity**: Critical

**What to look for**: `db.Table().Do(...)` containing `s.Execute(...)` (or `s.StreamExecuteScanQuery(...)`) on a `SELECT` followed by `for res.NextResultSet(...) { for res.NextRow() { ... } }` — without an outer keyset-pagination loop driving the read to exhaustion, and without an explicit `res.Truncated()` check. Equivalently: any code where one `Execute` call is treated as "the complete result that matched the filter".

**Problem**: Table Service caps query results at 1000 rows by default. The cap is server-side and silent — code that processes the returned rows runs to completion with `err == nil` even when the underlying query matched more.

The bug is data-dependent and emerges at scale. While the filtered result stays under 1000 rows (small dataset, narrow filter, dev environment), the function works correctly and tests pass. The day the `WHERE` clause first matches 1001 rows in production, the function processes the first 1000 and proceeds — no exception, no warning, no metric, no log line. The remaining rows are dropped on the floor.

The consequence is silent correctness corruption at the application layer:

- Billing pipeline reads "all unbilled usage items, charge the customer" — once unbilled items first exceed 1000, the next run under-charges by N and the discrepancy compounds every cycle.
- A migration job reads "all rows where `migrated = false`" — leaves N rows behind on every batch, work that never completes.
- A reconciliation pass reads "all transactions for the period" — silently misses N records, the totals stop matching the source system.
- A notification dispatcher reads "all customers with overdue invoices" — N customers don't get notified.

There is no signal until someone notices a downstream discrepancy, usually weeks or quarters later.

The 1000-row cap is a deliberate design constraint, not a knob to raise. The SDK uses it as a **forcing function**: code that talks to YDB must be written to *exhaust* a result set from day one, not to assume that one `Execute` call returns everything that matched. The correct architectural pattern is keyset pagination driven by an outer loop running until the page comes back empty, or reading through the Query Service streaming path. "Add a `LIMIT` clause" or "request a higher cap" both miss the point — they preserve the broken assumption that the application can fit any matching set in one call.

`ydb-go-sdk/v3` surfaces the truncation as a non-retryable error from `session.Execute` (an improvement over v2, which only set a `Truncated()` flag the caller had to check). Code that catches the error and retries past it, or that runs against the streaming variant where truncation is reported only via the flag, reproduces the original v2 bug.

**Fix**: drive the read to exhaustion through keyset pagination.

```go
const pageSize = 1000

var lastID uint64
for {
    var seen int
    err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        res, err := s.Query(ctx,
            `DECLARE $lastID AS Uint64;
             DECLARE $pageSize AS Uint64;
             SELECT user_id, amount FROM usage_items
             WHERE billed = false AND user_id > $lastID
             ORDER BY user_id
             LIMIT $pageSize`,
            query.WithParameters(ydb.ParamsBuilder().
                Param("$lastID").Uint64(lastID).
                Param("$pageSize").Uint64(pageSize).
                Build()),
        )
        if err != nil {
            return err
        }
        defer res.Close(ctx)
        // iterate result set, charge each row, update lastID = max(user_id) seen
        // increment `seen` per row processed
        return nil
    }, query.WithIdempotent())
    if err != nil {
        return err
    }
    if seen == 0 {
        return nil // exhausted
    }
}
```

The structure — outer `for` loop, keyset predicate (`> $lastID ORDER BY ... LIMIT`), termination when a page returns empty — is the design contract. The SDK call inside is just the transport.

**Source**: `ydb-platform/ydb-go-sdk/MIGRATION_v2_v3.md` section "About truncated result" — documents the 1000-row default cap and v3's non-retryable-error behavior. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/MIGRATION_v2_v3.md>. YDB Query Service is the streaming-by-default surface for reads that need to exhaust a result: <https://ydb.tech/docs/en/reference/ydb-sdk/>.
