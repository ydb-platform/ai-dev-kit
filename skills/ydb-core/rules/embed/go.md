# Go SDK (`ydb-go-sdk/v3`) — driver / session anti-patterns

Driver-construction and session-lifecycle rules. Query/transaction rules: `../../ydb-table/rules/embed/go.md`.

### RULE-GO-11: Long-lived session stored on the application side

**Severity**: High

**What to look for**: `db.Query().CreateSession(ctx)` (or legacy `db.Table().CreateSession(ctx)`) whose result is stored on a struct field, package-level variable, or any holder that outlives a single operation. Includes `sync.Once`-initialized package sessions and helpers that open one session and run many `s.Query(...)` / `s.Execute(...)` calls in a loop without going back through `Do`/`DoTx`.

**Problem**: a session held outside the pool pins to one node, ignores `shutdownHint` (server's drain signal), and surfaces `BAD_SESSION` to the caller when the server eventually closes it. The pool's per-call checkout is also the load-spreading mechanism; a held session bypasses the configured balancer.

**Fix**: drop the stored session, replace each call site with `db.Query().Do(ctx, func(ctx context.Context, s query.Session) error { ... }, query.WithIdempotent())` (or `db.Table().Do(...)` for Table Service).

**Source**: `ydb-platform/ydb-go-sdk/query/client.go` — `Do` godoc and pool semantics. `internal/meta/headers.go` and `tests/integration/hint_session_balancer_test.go` — `session-balancer` capability. <https://github.com/ydb-platform/ydb-go-sdk/blob/master/query/client.go>.
