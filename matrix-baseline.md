# Matrix baseline — 2026-06-25 (Haiku grader, C++ audit rules)

Snapshot of the A/B compatibility matrix after landing `RULE-CPP-01`…`RULE-CPP-11`
(`skills/ydb-table/rules/embed/cpp.md`, `references/embed/cpp.md`, 11 promptfoo tests).
Future edits to skills should be compared against this — a meaningful change should move
cells from `REDUNDANT` / `INSUFFICIENT` toward `SKILL_WORKS` without regressing
`SKILL_WORKS` cells.

> **Snapshot scope (2026-06-25).** Same grader (`anthropic/claude-haiku-4.5`).
> **11 providers × 39 tests = 429 cells** per side. Skill side: `eval-njF` +
> error retry `eval-J6T`. Bare side: `eval-WWx` (clean run, 0 errors).

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_API_BASE_URL="https://api.eliza.yandex.net/raw/openrouter/v1"
npx promptfoo@latest eval --no-cache -j 4                                # skill loaded
npx promptfoo@latest eval --filter-errors-only eval-njF-2026-06-25T11:39:41 --no-cache -j 4
npx promptfoo@latest eval -c promptfooconfig.bare.yaml --no-cache -j 4   # bare control
python3 scripts/ab-compare.py \
    --skill eval-njF-2026-06-25T11:39:41 \
    --skill-retry eval-J6T-2026-06-25T15:22:13 \
    --bare  eval-WWx-2026-06-26T10:12:43
```

- **11 providers** × **39 tests** = 429 cells per side.
- Skill side: `eval-njF` (2h 29m, concurrency 4) — 359 pass, 31 fail, 39 transport
  errors on first pass. Retry `eval-J6T` (8m 30s) — 83/88 recovered, 0 errors.
- Bare side: `eval-WWx` (1h 21m, concurrency 4) — 50 pass, 379 fail, 0 errors.
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
skill eval: eval-njF-2026-06-25T11:39:41 + retry eval-J6T-2026-06-25T15:22:13
bare eval:  eval-WWx-2026-06-26T10:12:43
grader:     anthropic/claude-haiku-4.5

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     347  ( 80.9%)
  . REDUNDANT        46  ( 10.7%)
  x INSUFFICIENT     32  (  7.5%)
  ! SKILL_HARMS       4  (  0.9%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  C++ audit · Custom Sleep retrier around YDB calls (RULE     8     0     3     0
  C++ audit · DDL (ExecuteSchemeQuery) inside RetryOperat    10     0     1     0
  C++ audit · Explicit BeginTransaction when fused TTxCon    11     0     0     0
  C++ audit · External state mutation in retry lambda (RU    11     0     0     0
  C++ audit · INSERT INTO inside .Idempotent(true) retry     11     0     0     0
  C++ audit · Missing Idempotent on RetryQuerySync (RULE-     9     0     2     0
  C++ audit · Non-parametrized YQL via std::format (RULE-    11     0     0     0
  C++ audit · Outer for loop around RetryQuerySync (RULE-    10     0     1     0
  C++ audit · StreamExecuteQuery without duplicate handli    11     0     0     0
  C++ audit · TDriver constructed per request instead of     11     0     0     0
  C++ audit · Unbounded Table read without pagination (RU    10     1     0     0
  Core · Cloud auth without hardcoded credentials             2     7     1     1
  Core · Local Docker + Python quickstart                     7     3     0     1
  Core · Onboarding — 3-minute YDB intro for a newcomer       8     3     0     0
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      6     5     0     0
  Go audit · Explicit BeginTransaction before first query     8     1     1     1
  Go audit · External state mutation from Do retry closur    11     0     0     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     6     0     5     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        8     2     1     0
  Go audit · Nested Do call (RULE-GO-06)                      3     8     0     0
  Go audit · Non-interactive DoTx auto-commit without `qu     9     0     2     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx    10     0     1     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G     8     3     0     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU    10     0     1     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren    11     0     0     0
  Go audit · Reading all matching rows through Table Serv    10     0     1     0
  Go audit · Separate Commit after last query (RULE-GO-10     7     0     4     0
  Go audit · Stats consumed before stream drain (RULE-GO-    11     0     0     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv     7     3     1     0
  Go audit · for-loop wrapping Do (RULE-GO-04)               10     1     0     0
  Java audit · JDBC batching not configured (RULE-JV-02)      5     5     1     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            11     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           8     3     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       11     0     0     0
  Java audit · findById in a loop (RULE-JV-01)               11     0     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    11     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                11     0     0     0
  Query · Keyset pagination in YQL + Go                       8     0     3     0
  Query · Primary-key design for IoT events (monotonic-PK     6     1     3     1

──────────────────────────────────────────────────────────────────────────────
SKILL_HARMS + INSUFFICIENT cells
──────────────────────────────────────────────────────────────────────────────
  ! SKILL_HARMS    Frontier · Anthropic Opus 4.7             Core · Cloud auth without hardcoded credentials
  ! SKILL_HARMS    Frontier · OpenAI GPT-5.3 Codex           Core · Local Docker + Python quickstart
  ! SKILL_HARMS    Frontier OSS · Z.ai GLM 4.7               Go audit · Explicit BeginTransaction before first query
  ! SKILL_HARMS    Frontier · Google Gemini 3.1 Pro (preview)  Query · Primary-key design for IoT events (monotonic-PK)

  x INSUFFICIENT (32)
  Frontier OSS · MiniMax M2.7               C++ audit · Custom Sleep retrier (RULE-CPP-05)
  Frontier OSS · Z.ai GLM 4.7               C++ audit · Custom Sleep retrier (RULE-CPP-05)
  Laptop · Qwen3.6 35B-A3B                  C++ audit · Custom Sleep retrier (RULE-CPP-05)
  Frontier OSS · Z.ai GLM 4.7               C++ audit · DDL inside RetryOperation (RULE-CPP-02)
  Laptop · Mistral Small 2603               C++ audit · Missing Idempotent on RetryQuerySync (RULE-CPP-06)
  Laptop · OpenAI gpt-oss-20b               C++ audit · Missing Idempotent on RetryQuerySync (RULE-CPP-06)
  Laptop · Mistral Small 2603               C++ audit · Outer for loop around RetryQuerySync (RULE-CPP-04)
  Frontier OSS · Moonshot Kimi K2.6         Core · Cloud auth without hardcoded credentials
  Laptop · OpenAI gpt-oss-20b               Go audit · Explicit BeginTransaction before first query
  Frontier OSS · Z.ai GLM 4.7               Go audit · Interactive Table Service `tx.CommitTx`
  Frontier · Google Gemini 3.1 Pro (preview)  Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · Mistral Small 2603               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · Qwen3.6 35B-A3B                  Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Missing WithIdempotent on Do (RULE-GO-03)
  Laptop · Mistral Small 2603               Go audit · Non-interactive DoTx auto-commit without `query`
  Laptop · OpenAI gpt-oss-20b               Go audit · Non-interactive DoTx auto-commit without `query`
  Laptop · Mistral Small 2603               Go audit · Non-interactive DoTx without `ydb.WithLazyTx`
  Frontier OSS · Z.ai GLM 4.7               Go audit · PreferLocalDC / PreferNearestDC balancer
  Laptop · Qwen3.6 35B-A3B                  Go audit · Reading all matching rows through Table Service
  Frontier OSS · DeepSeek v4-Pro            Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · Mistral Small 2603               Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · OpenAI gpt-oss-20b               Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · Qwen3.6 35B-A3B                  Go audit · Separate Commit after last query (RULE-GO-10)
  Laptop · OpenAI gpt-oss-20b               Go audit · `ydb.WithIgnoreTruncated` masking Table Service limits
  Laptop · OpenAI gpt-oss-20b               Java audit · JDBC batching not configured (RULE-JV-02)
  Frontier OSS · Z.ai GLM 4.7               Query · Keyset pagination in YQL + Go
  Frontier · Google Gemini 3.1 Pro (preview)  Query · Keyset pagination in YQL + Go
  Frontier · OpenAI GPT-5.3 Codex           Query · Keyset pagination in YQL + Go
  Frontier OSS · DeepSeek v4-Pro            Query · Primary-key design for IoT events (monotonic-PK)
  Frontier OSS · Z.ai GLM 4.7               Query · Primary-key design for IoT events (monotonic-PK)
  Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events (monotonic-PK)
```

For the full per-cell breakdown (429 rows), re-run:

```bash
python3 scripts/ab-compare.py \
  --skill eval-njF-2026-06-25T11:39:41 \
  --skill-retry eval-J6T-2026-06-25T15:22:13 \
  --bare eval-WWx-2026-06-26T10:12:43
```

Raw pass/fail grids (skill side and bare side separately): `npx promptfoo@latest view`
or export with `npx promptfoo@latest export eval <eval-id>`.

## Open follow-ups

- **INSUFFICIENT cluster · Go-SDK tx-control rules** — largest non-C++ bucket
  (`tx.CommitTx`, `Separate Commit after last query`, `Non-interactive DoTx` variants).
- **INSUFFICIENT cluster · C++ Laptop/OSS models** — 7 cells on CPP-05 (custom sleep),
  CPP-02 (DDL in retry), CPP-06 (missing Idempotent), CPP-04 (outer loop). Mostly
  missing or wrong `RULE-CPP-NN` citation on weaker models.
- **SKILL_HARMS · four cells** — Opus + Cloud auth, Codex + Local Docker quickstart,
  GLM + Go BeginTransaction, Gemini + Query PK design. Inspect skill-vs-bare outputs
  before trimming surrounding content.
- **Skill-side transport errors on long Eliza runs** — `eval-njF` hit 429/timeouts;
  `--filter-errors-only` + `--skill-retry` recovered all 39. Use `-j 2` or `-j 1`
  if rate limits persist.
