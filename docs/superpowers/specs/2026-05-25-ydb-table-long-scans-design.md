# Design: long scans and resumable reads in `ydb-table` references

**Date:** 2026-05-25
**Surface:** `skills/ydb-table`
**Scope:** references only (no rule additions)

## Motivation

Auditing the six retry tips at `ydb-platform/tips_and_tricks/tips/02_retry/{02,04,05,06,07,09}.md` against the existing Go ruleset showed that five tips are already covered:

| Tip | Existing coverage |
|---|---|
| `02_custom_retry` | RULE-GO-05 (custom retrier with `time.Sleep`) |
| `04_closure_temp_objects` | RULE-GO-02 (external state mutation from `Do`/`DoTx` closure) |
| `05_no_cleanup` | RULE-GO-02 (same — accumulation into outer slice) |
| `07_no_idempotency_flag` | RULE-GO-03 (missing / mis-set `WithIdempotent`) |
| `09_retry-inside-retry` | RULE-GO-06 (nested `Do`/`DoTx`) |

Only `06_streaming_queries` opens a topic that the surface skill does not currently cover: **how application code should structure a read that returns far more rows than a single streaming `s.Query(...)` call should be carrying in one retry-scope.** `references/working-with-data.md` covers writes (batch via `AS_TABLE`, bulk-upsert) and transaction modes but has no read-shape section; `references/embed/go.md` mentions pagination only obliquely via the cross-ref in RULE-GO-01 (1000-row cap fix).

The maintainer instruction in memory (`feedback_no_cross_language_extrapolation.md`) constrains this work to references — no new rule IDs.

## Grounding sources (verified)

- **`https://ydb.tech/docs/en/dev/paging`** — official YDB pagination recipe. Verbatim: *"To organize paginated output, we recommend selecting data sorted by primary key sequentially, limiting the number of rows with the LIMIT keyword."* Canonical query shape uses tuple comparison `WHERE (city, number) > ($lastCity, $lastNumber) ORDER BY city, number LIMIT $limit`. Caveat: *"Tuples are compared element by element from left to right, so the order of the fields in the tuple must match the order of the fields in the primary key to avoid table full scan."* Caveat on NULL: *"using NULL as key column values is highly discouraged, since the SQL standard doesn't allow NULL to be compared."*
- **`https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/pagination/main.go`** — canonical Go embodiment. Confirmed shape: outer `for i, empty := 0, false; i < maxPages && !empty; i++` driving a `selectPaging(ctx, ..., limit, &lastNum, &lastCity)` helper; cursor `(lastNum, lastCity)` lives in caller-side variables passed by pointer through each iteration; loop terminates on `empty` (page returned <limit rows).
- **`ydb-platform/ydb-go-sdk/MIGRATION_v2_v3.md`** — already cited from RULE-GO-01; documents Query Service streaming vs Table Service 1000-row cap.

Tips_and_tricks tip `06_streaming_queries` itself is treated as **direction-finding only**, not as a citation. Its Go example uses `LIMIT ... OFFSET ...` which contradicts the canonical YDB recipe — the spec rejects that shape.

## Changes

### A. `skills/ydb-table/references/working-with-data.md` — new section

**Title:** `Reading many rows: long scans and resumable reads`

**Placement:** After `When to write which way`, before `Related`. The file's existing arc is "transaction modes → writes → cross-section guidance"; this section adds the read counterpart before the closing cross-refs.

**Content (~150-220 words, language-agnostic):**

1. *Tension.* A single `SELECT` that returns "all matching rows" via the streaming call surface is one retry unit. A transient failure mid-stream restarts the closure — every already-streamed row is re-read. The cost scales with the size of the match, not the size of the failure.

2. *Recipe.* Keyset pagination by primary key — the canonical YDB pattern. Outer caller-side loop, each iteration reads one bounded batch:

   ```yql
   SELECT ...
   FROM t
   WHERE (pk1, pk2, ...) > ($cur1, $cur2, ...)
   ORDER BY pk1, pk2, ...
   LIMIT $batch;
   ```

   The tuple's field order must match the primary key's field order — otherwise the predicate is non-index-friendly and degenerates to a full table scan. Terminate the outer loop when a page returns fewer rows than `$batch` (or zero).

3. *Why this beats one big `SELECT`.* Each batch is its own retry scope — a failure replays only the current batch, not everything accumulated. Each batch is idempotent (key-ranged read), so the SDK retrier handles it under the standard `WithIdempotent` semantics. Memory pressure is bounded by `$batch`.

4. *Resumability across process restarts.* The cursor lives in caller-side memory by default. To resume after a process restart, persist the cursor outside YDB (or in a separate state table) — the SDK has no built-in checkpoint API; checkpoints are application-level.

5. *NULL in key columns.* Discouraged — tuple comparison with NULL is undefined under the SQL standard, so the cursor predicate misbehaves.

6. *Anti-pattern.* `LIMIT ... OFFSET $n` for large `$n` — each page re-scans the rows skipped by `OFFSET`, so cost grows quadratically with page index. The recipe is keyset.

7. *Cross-refs.* Source: `https://ydb.tech/docs/en/dev/paging`. For the related Table-Service-specific anti-pattern (one `s.Execute` "reads everything matching" + the 1000-row cap), see `rules/embed/go.md` RULE-GO-01.

### B. `skills/ydb-table/references/embed/go.md` — new subsection

**Title:** `Long scans / resumable reads`

**Placement:** Between the existing `Retries` and `Bulk upsert` sections — sits naturally between "how retry classifies errors" and "how to ingest many rows," and it's adjacent to RULE-GO-01's cross-ref.

**Content (~80-130 words + small code block):**

Two-sentence preamble: same tension framed for Go (one `s.Query` over a wide range is one retry unit; outer keyset loop turns it into many small retry units). Cross-ref the YDB-level recipe in `../working-with-data.md` so the YDB-level claim isn't repeated.

Code block — keyset cursor loop, single-column PK to keep the snippet small:

```go
var cursor uint64
const batch = 1000
for {
    var page []row
    err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
        var local []row
        res, err := s.Query(ctx,
            `SELECT id, payload FROM t
             WHERE id > $cursor
             ORDER BY id
             LIMIT $batch;`,
            query.WithParameters(ydb.ParamsBuilder().
                Param("$cursor").Uint64(cursor).
                Param("$batch").Uint64(batch).
                Build()),
        )
        if err != nil { return err }
        defer func() { _ = res.Close(ctx) }()
        // scan res into local
        page = local
        return nil
    }, query.WithIdempotent())
    if err != nil { return err }
    if len(page) == 0 { break }
    // process page, advance cursor to last row's id
    cursor = page[len(page)-1].id
    if len(page) < batch { break }
}
```

Cross-refs:

- `https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/pagination/main.go` — upstream form (compound PK, helper function shape).
- `rules/embed/go.md` RULE-GO-01 — related anti-pattern (Table Service `s.Execute` over unbounded range + 1000-row cap).
- `RULE-GO-02` / `RULE-GO-03` are silently respected by the snippet (`local` built inside, assigned on success; `WithIdempotent` set because the SELECT is idempotent) — no need to call out.

### C. Things deliberately not done

- **No new rule ID.** Streaming-without-cursor-loop shape is too soft for an LLM auditor (false-positive risk; many legitimate small reads also use a single `s.Query`). Per `feedback_no_cross_language_extrapolation.md`, rules wait for the maintainer.
- **No checkpoint API description.** The SDK has none; describing application-level checkpoint shapes (Kafka offsets, separate state tables, file cursors) is YAGNI for this skill — the user can persist the cursor however they want.
- **No Java/Python/C++ embed work.** Out of scope per the chosen approach.
- **No edit to `working-with-data.md`'s existing sections.** Only an additive insertion.

## Verification before commit

Run from repo root:

```
# language-agnostic invariant on working-with-data.md
grep -iE 'jdbc|hibernate|spring|java|jpa|python|golang|\.net|dotnet|csharp' \
  skills/ydb-table/references/working-with-data.md

# both new URLs must be HTTP 200
curl -sIL https://ydb.tech/docs/en/dev/paging | head -1
curl -sIL https://github.com/ydb-platform/ydb-go-sdk/blob/master/examples/pagination/main.go | head -1
```

First command must produce no output. Second and third must show `200`.

Soft check: `wc -c skills/ydb-table/references/embed/go.md` stays under ~8000 bytes (currently 6461 bytes; the subsection adds roughly 700-900 bytes including the code block).

## Out of scope (future work)

- Whether to fold tip 06's checkpoint concept into a topics-side reference is a separate question (different semantics — consumer offsets vs. PK cursor). Not addressed here.
- Whether RULE-GO-01's "Switch to Query Service streaming" branch should be re-worded to nudge toward keyset-loop on very large matches is a follow-up edit, gated on the maintainer wanting it.
- Java/Python/C++ embed equivalents of this section are also follow-ups.
