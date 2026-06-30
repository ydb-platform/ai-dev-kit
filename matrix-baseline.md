# Matrix baseline — 2026-06-29 (Haiku grader, C++ review fixes)

Snapshot of the A/B compatibility matrix after PR #6 review fixes: ydb.tech-grounded
C++ docs (`references/embed/cpp.md`, `rules/embed/cpp.md`), CPP-06/08/09 test snippet
updates, and routing config aligned with the main matrix (Mistral Small 2603, GLM,
MiniMax, Haiku grader for routing llm-rubric).

Future edits to skills should be compared against this — a meaningful change should move
cells from `REDUNDANT` / `INSUFFICIENT` toward `SKILL_WORKS` without regressing
`SKILL_WORKS` cells.

> **Snapshot scope (2026-06-29).** Same grader (`anthropic/claude-haiku-4.5`).
> **11 providers × 39 tests = 429 cells** per side. Skill side: `eval-LnN`.
> Bare side: `eval-NqX`. Both completed with 0 transport errors.

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
npx promptfoo@latest eval --no-cache -j 4                                # skill loaded
npx promptfoo@latest eval -c promptfooconfig.bare.yaml --no-cache -j 4   # bare control
python3 scripts/ab-compare.py \
    --skill eval-LnN-2026-06-29T09:45:55 \
    --bare  eval-NqX-2026-06-29T13:28:35
```

- **11 providers** × **39 tests** = 429 cells per side.
- Skill side: `eval-LnN` (concurrency 4) — 398 pass, 31 fail, 0 errors.
- Bare side: `eval-NqX` (concurrency 4) — 46 pass, 383 fail, 0 errors.
- Routing matrix (separate config): `eval-uKD-2026-06-29T09:39:50` — 79/99 pass.
- Reasoning disabled only on Moonshot Kimi K2.6 — other providers reject the flag.
  Qwen3.6 35B-A3B and OpenAI gpt-oss-20b keep reasoning on with `max_tokens` bumped
  to 8192. See [`docs/testing.md`](docs/testing.md#speed-knobs).

## Provider mix

Three tiers:

- **Frontier · closed** (3): Anthropic Opus 4.7, OpenAI GPT-5.3 Codex,
  Google Gemini 3.1 Pro (preview).
- **Frontier · open-source** (5): DeepSeek v4-Pro, Moonshot Kimi K2.6,
  Qwen3.6 Plus, Z.ai GLM 4.7, MiniMax M2.7.
- **Laptop · Ollama-runnable** (3): OpenAI gpt-oss-20b, Mistral Small 2603,
  Qwen3.6 35B-A3B.

When iterating on skill content, run only the Laptop tier — frontier models tend to
answer correctly from training memory regardless of skill content, so they're a poor
signal for whether an edit moved anything.

```bash
npx promptfoo@latest eval --filter-providers 'Laptop'
```

## How to read it

Each cell is one (provider, test) pair, classified by comparing the main matrix
verdict against the bare-control verdict:

| Quadrant       | skill | bare | Meaning                                      |
|----------------|-------|------|----------------------------------------------|
| `SKILL_WORKS`  | PASS  | FAIL | The skill earned the answer. **Keep.**       |
| `REDUNDANT`    | PASS  | PASS | The model already knew. Candidate for trim.  |
| `INSUFFICIENT` | FAIL  | FAIL | Skill text isn't enough — investigate.       |
| `SKILL_HARMS`  | FAIL  | PASS | Skill confused the model. Investigate.       |

## Snapshot

```
skill eval: eval-LnN-2026-06-29T09:45:55
bare eval:  eval-NqX-2026-06-29T13:28:35
grader:     anthropic/claude-haiku-4.5

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     352  ( 82.1%)
  . REDUNDANT        46  ( 10.7%)
  x INSUFFICIENT     31  (  7.2%)
  ! SKILL_HARMS       0  (  0.0%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  C++ audit · Custom Sleep retrier around YDB calls (RULE    11     0     0     0
  C++ audit · DDL (ExecuteSchemeQuery) inside RetryOperat    11     0     0     0
  C++ audit · Explicit BeginTransaction when fused TTxCon    11     0     0     0
  C++ audit · External state mutation in retry lambda (RU    10     1     0     0
  C++ audit · INSERT INTO inside .Idempotent(true) retry     11     0     0     0
  C++ audit · Missing Idempotent on RetryQuerySync (RULE-    11     0     0     0
  C++ audit · Non-parametrized YQL via std::format (RULE-    10     1     0     0
  C++ audit · Outer for loop around RetryQuerySync (RULE-    11     0     0     0
  C++ audit · StreamExecuteQuery without duplicate handli    11     0     0     0
  C++ audit · TDriver constructed per request instead of     11     0     0     0
  C++ audit · Unbounded Table read without pagination (RU    10     1     0     0
  Core · Cloud auth without hardcoded credentials             6     5     0     0
  Core · Local Docker + Python quickstart                     9     2     0     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       8     3     0     0
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      7     4     0     0
  Go audit · Explicit BeginTransaction before first query     9     1     1     0
  Go audit · External state mutation from Do retry closur    10     1     0     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     6     0     5     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        9     1     1     0
  Go audit · Nested Do call (RULE-GO-06)                      4     7     0     0
  Go audit · Non-interactive DoTx auto-commit without `qu     9     0     2     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx     9     0     2     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G    10     1     0     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU     9     0     2     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren     9     0     2     0
  Go audit · Reading all matching rows through Table Serv     8     0     3     0
  Go audit · Separate Commit after last query (RULE-GO-10     8     0     3     0
  Go audit · Stats consumed before stream drain (RULE-GO-     9     1     1     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv    11     0     0     0
  Go audit · for-loop wrapping Do (RULE-GO-04)                8     2     1     0
  Java audit · JDBC batching not configured (RULE-JV-02)      3     8     0     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            11     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           6     5     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       10     0     1     0
  Java audit · findById in a loop (RULE-JV-01)               11     0     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    11     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                10     1     0     0
  Query · Keyset pagination in YQL + Go                       9     0     2     0
  Query · Primary-key design for IoT events (monotonic-PK     5     1     5     0

──────────────────────────────────────────────────────────────────────────────
SKILL_HARMS + INSUFFICIENT cells
──────────────────────────────────────────────────────────────────────────────
  (no SKILL_HARMS cells)

  x INSUFFICIENT (31)
  Laptop · OpenAI gpt-oss-20b               Go audit · Explicit BeginTransaction before first query
  Frontier OSS · Moonshot Kimi K2.6         Go audit · Interactive Table Service `tx.CommitTx`
  Frontier OSS · Z.ai GLM 4.7               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · Mistral Small 2603               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · Qwen3.6 35B-A3B                  Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Missing WithIdempotent on Do (RULE-GO-03)
  Frontier OSS · MiniMax M2.7               Go audit · Non-interactive DoTx auto-commit without `query`
  Laptop · OpenAI gpt-oss-20b               Go audit · Non-interactive DoTx auto-commit without `query`
  Frontier OSS · MiniMax M2.7               Go audit · Non-interactive DoTx without `ydb.WithLazyTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Non-interactive DoTx without `ydb.WithLazyTx`
  Frontier OSS · DeepSeek v4-Pro            Go audit · PreferLocalDC / PreferNearestDC balancer
  Laptop · OpenAI gpt-oss-20b               Go audit · PreferLocalDC / PreferNearestDC balancer
  Frontier OSS · MiniMax M2.7               Go audit · PreferNearestDC balancer (RULE-GO-08)
  Laptop · OpenAI gpt-oss-20b               Go audit · PreferNearestDC balancer (RULE-GO-08)
  Frontier OSS · Z.ai GLM 4.7               Go audit · Reading all matching rows through Table Service
  Frontier · Google Gemini 3.1 Pro (preview)  Go audit · Reading all matching rows through Table Service
  Laptop · Mistral Small 2603               Go audit · Reading all matching rows through Table Service
  Frontier OSS · Z.ai GLM 4.7               Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · Mistral Small 2603               Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · OpenAI gpt-oss-20b               Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · Qwen3.6 35B-A3B                  Go audit · Stats consumed before stream drain (RULE-GO-11)
  Laptop · OpenAI gpt-oss-20b               Go audit · for-loop wrapping Do (RULE-GO-04)
  Laptop · OpenAI gpt-oss-20b               Java audit · deleteAllById on bulk path (RULE-JV-04)
  Frontier OSS · MiniMax M2.7               Query · Keyset pagination in YQL + Go
  Frontier · Google Gemini 3.1 Pro (preview)  Query · Keyset pagination in YQL + Go
  Frontier OSS · DeepSeek v4-Pro            Query · Primary-key design for IoT events (monotonic-PK)
  Frontier OSS · MiniMax M2.7               Query · Primary-key design for IoT events (monotonic-PK)
  Frontier OSS · Z.ai GLM 4.7               Query · Primary-key design for IoT events (monotonic-PK)
  Laptop · Mistral Small 2603               Query · Primary-key design for IoT events (monotonic-PK)
  Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events (monotonic-PK)
```

For the full per-cell breakdown (429 rows), re-run:

```bash
python3 scripts/ab-compare.py \
  --skill eval-LnN-2026-06-29T09:45:55 \
  --bare  eval-NqX-2026-06-29T13:28:35
```

Raw pass/fail grids (skill side and bare side separately): `npx promptfoo@latest view`
or export with `npx promptfoo@latest export eval <eval-id>`.

## Open follow-ups

- **INSUFFICIENT cluster · Go-SDK tx-control rules** — largest remaining bucket
  (`tx.CommitTx`, `Separate Commit after last query`, `Non-interactive DoTx` variants,
  `PreferNearestDC` / `PreferLocalDC`).
- **INSUFFICIENT cluster · Query PK design** — 5 cells on monotonic-PK IoT scenario;
  mostly weaker OSS/Laptop models.
- **C++ audit tests** — all 11 rules at 10–11 `SKILL_WORKS` per test after review
  fixes (no C++ `INSUFFICIENT` cells in this snapshot).
