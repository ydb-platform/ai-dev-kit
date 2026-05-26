# Session lifecycle and resilience

## Pool

SDK owns sessions. Application borrows per operation via the pool wrapper (`Do`/equivalent), never holds a `Session` field across calls.

Server cap: 1000 concurrent sessions per node. Client-pool upper bound: `1000 × nodes × 2/3 / clients`.

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

No deadline propagation available: per-call timeout = `min(caller-deadline, 2-3 × p99_normal)` for that specific query. Tighter fires during stress and amplifies load via retries; looser holds sessions for results no caller wants.

Upstream provides a deadline: forward it. Request no longer needed: cancel the context — for YDB that closes the session = server-side cancel.

## Warmup

First call pays session-creation cost. For flat startup latency, fire a few concurrent `SELECT 1` against `/.metadata` at boot to prime the pool across nodes.
