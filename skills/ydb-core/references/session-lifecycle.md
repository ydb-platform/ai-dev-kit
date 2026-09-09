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

## Deadlines and cancellation

Docs: <https://ydb.tech/docs/en/dev/timeouts>. Multiple timeouts (operation, transport, cancel-after); set all.

Treat the upstream request deadline as one end-to-end budget. Session acquisition, retry backoff, every attempt, the RPC itself, and result-stream draining all spend from that same budget. Before starting YDB work, cap the remaining caller budget by the operation's normal service limit; never give every retry a fresh full timeout.

Per-call timeout sizing: `min(caller deadline remaining, 2-3 × p99_normal)` for that specific query. Tighter starts firing on requests that would have succeeded under stress (rolling restart, drill entry) and amplifies load via retries; looser keeps work alive after the caller stopped caring, holding pool slots.

Propagate the caller's cancellation through the SDK's request-lifecycle mechanism instead of detaching work onto a root context or an unrelated fixed timeout. Cancellation is best-effort: it can stop local retry orchestration and can notify the transport, but it is not evidence that an already-running request stopped or that a write rolled back. Keep retry and side-effect safety correct for an uncertain result.

## Warmup

First call pays session-creation cost. For flat startup latency, fire a few concurrent `SELECT 1` queries at boot to prime the pool across nodes.
