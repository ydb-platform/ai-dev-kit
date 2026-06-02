# Session lifecycle and resilience

## Pool

SDK owns sessions. Application borrows per operation via the pool wrapper (`Do`/equivalent), never holds a `Session` field across calls.

Each YDB node enforces a concurrent-session cap. Size client pools to stay well under that bound, with headroom for the cross-DC degraded scenario (one DC of N becoming unreachable).

## `shutdownHint`

Server marks a session for drain by setting `shutdownHint` in response metadata. SDK response: stop new ops on that session, let in-flight finish, discard, take a fresh one.

Ignored hint → server closes the session → next call gets `BAD_SESSION`. Shows up as `BAD_SESSION` spikes during rolling restart / DC drill.

SDKs auto-attach the `session-balancer` capability header. Requires going through the pool API; sessions held in application state bypass this.

## Retries

SDK classifies errors into three buckets: non-retryable, unconditionally-retryable, conditionally-retryable. Conditional bucket (transport drops, session loss) replays only when the call is marked idempotent.

Mark idempotent work explicitly. Per-language symbol name in `embed/`.

Non-idempotent writes (counter increment, unkeyed `INSERT`) must not carry the idempotency flag — make them idempotent first (client-generated request id, dedup table) and only then opt in.

No hand-rolled retry loops with fixed sleeps. They replay non-retryable errors, burn budget, and replay conditional failures without the idempotency gate (can double-apply non-idempotent writes).

## Timeouts

Docs: <https://ydb.tech/docs/en/dev/timeouts>. Multiple timeouts (operation, transport, cancel-after); set all.

Per-call timeout sizing: `min(caller-deadline, 2-3 × p99_normal)` for that specific query. Tighter starts firing on requests that would have succeeded under stress (rolling restart, drill entry) and amplifies load via retries; looser keeps in-flight requests alive after the caller stopped caring, holding pool slots.

When the application receives a deadline from upstream, forward it (deadline propagation) instead of using a fixed per-call timeout. When the request is no longer needed, cancel its context — the SDK propagates the cancel to YDB so the server aborts the in-flight gRPC call.

## Warmup

First call pays session-creation cost. For flat startup latency, fire a few concurrent `SELECT 1` queries at boot to prime the pool across nodes.
