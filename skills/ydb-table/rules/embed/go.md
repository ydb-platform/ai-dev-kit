# Go SDK (`ydb-go-sdk/v3`) — anti-patterns

Audit rules for application code talking to YDB through the Go SDK. Each rule is self-contained: the surface skill must produce correct audit output on its own.

### RULE-GO-01: Reading "all matching rows" through Table Service without pagination

**Severity**: Critical

**What to look for**: `s.Execute(ctx, ..., "SELECT ...")` or `s.StreamExecuteScanQuery(...)` inside `db.Table().Do(...)`, with no outer keyset-pagination loop and no `res.Truncated()` check.

**Problem**: Table Service caps query results at 1000 rows by default. The cap is server-side and silent — once the matching set exceeds 1000, the call returns `err == nil` with the first 1000 rows and the rest are dropped. The bug is data-dependent: appears only when the `WHERE` clause first crosses the threshold in production, with no signal until a downstream discrepancy surfaces. The cap is a design constraint, not a knob — code must be written to exhaust the result through keyset pagination or Query Service streaming from day one. "Add a `LIMIT`" or "raise the cap" preserve the broken assumption.

**Fix**:

```go
const pageSize = 1000
var lastID uint64
for {
    var seen int
    err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        res, err := s.Query(ctx,
            `DECLARE $lastID AS Uint64;
             SELECT user_id, amount FROM usage_items
             WHERE billed = false AND user_id > $lastID
             ORDER BY user_id LIMIT 1000`,
            query.WithParameters(ydb.ParamsBuilder().
                Param("$lastID").Uint64(lastID).Build()),
        )
        if err != nil { return err }
        defer res.Close(ctx)
        // process page, update lastID, increment seen
        return nil
    }, query.WithIdempotent())
    if err != nil { return err }
    if seen == 0 { return nil }
}
```

**Source**: `ydb-platform/ydb-go-sdk/MIGRATION_v2_v3.md` — section "About truncated result" documents the 1000-row default and the v3 non-retryable-error behavior. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/MIGRATION_v2_v3.md>.
