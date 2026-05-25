# Matrix baseline — 2026-05-25 (Haiku grader)

Snapshot of the A/B compatibility matrix at a known-good point. Future
edits to skills should be compared against this — a meaningful change
should move cells from `REDUNDANT` / `INSUFFICIENT` toward `SKILL_WORKS`
without regressing `SKILL_WORKS` cells.

> **Methodology refresh, 2026-05-25 (this snapshot).** The rubric grader
> switched from `anthropic/claude-sonnet-4.6` to
> `anthropic/claude-haiku-4.5` — Haiku is ~10× cheaper and was
> pre-validated as systematically stricter (93.6% pass/fail agreement
> with Sonnet on skill-loaded outputs, 83.1% on bare-control outputs;
> disagreements concentrate on borderline rubric-clause enforcement,
> not noise). See `scripts/grader-agreement.py` for the validation
> method and `scripts/simulate-grader-swap.py` for the dry-run
> projection. The headline shifts below come from the grader swap, not
> from skill or test changes.

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
npx promptfoo@latest eval                                # skill loaded
npx promptfoo@latest eval -c promptfooconfig.bare.yaml   # bare control
python3 scripts/ab-compare.py
```

- **11 providers** × **27 tests** = 297 cells per side.
- Concurrency 12. **No transport / credit errors** — both sides
  completed in a single pass in ~12 min each (no retries needed this
  time, unlike the 2026-05-25 Sonnet baseline).
- Reasoning disabled only on Moonshot Kimi K2.6 — other providers reject
  the flag (`reasoning: { enabled: false }` → HTTP 400). For Qwen3.6
  35B-A3B and OpenAI gpt-oss-20b (also thinking models) we leave
  reasoning on and bump `max_tokens` to 8192 instead. See
  [`docs/testing.md`](docs/testing.md#speed-knobs).

## Provider mix

Three tiers:

- **Frontier · closed** (3): Anthropic Opus 4.7, OpenAI GPT-5.3 Codex,
  Google Gemini 3.1 Pro (preview).
- **Frontier · open-source** (5): DeepSeek v4-Pro, Moonshot Kimi K2.6,
  Qwen3.6 Plus, Z.ai GLM 4.7, MiniMax M2.7.
- **Laptop · Ollama-runnable** (3): OpenAI gpt-oss-20b, Mistral Devstral
  Small, Qwen3.6 35B-A3B.

When iterating on skill content, run only the Laptop tier — frontier
models tend to answer correctly from training memory regardless of skill
content, so they're a poor signal for whether an edit moved anything.

```bash
npx promptfoo@latest eval --filter-providers 'Laptop'
```

## How to read it

Each cell is one (provider, test) pair, classified by comparing the
main matrix verdict against the bare-control verdict:

| Quadrant       | skill | bare | Meaning                                      |
|----------------|-------|------|----------------------------------------------|
| `SKILL_WORKS`  | PASS  | FAIL | The skill earned the answer. **Keep.**       |
| `REDUNDANT`    | PASS  | PASS | The model already knew. Candidate for trim.  |
| `INSUFFICIENT` | FAIL  | FAIL | Skill text isn't enough — investigate.       |
| `SKILL_HARMS`  | FAIL  | PASS | Skill confused the model. Investigate.       |

## Snapshot

```
skill eval: eval-MSx-2026-05-25T12:59:55
bare eval:  eval-cI8-2026-05-25T13:00:02
grader:     anthropic/claude-haiku-4.5

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     211  ( 71.0%)
  . REDUNDANT        48  ( 16.2%)
  x INSUFFICIENT     35  ( 11.8%)
  ! SKILL_HARMS       3  (  1.0%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  Core · Cloud auth without hardcoded credentials             3     6     0     2
  Core · Local Docker + Python quickstart                     7     3     1     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       6     4     1     0
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      4     6     1     0
  Go audit · Explicit BeginTransaction before first query     8     1     2     0
  Go audit · External state mutation from Do retry closur     9     1     1     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     6     0     5     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        8     1     2     0
  Go audit · Nested Do call (RULE-GO-06)                      6     5     0     0
  Go audit · Non-interactive DoTx auto-commit without `qu    11     0     0     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx    11     0     0     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G     7     3     1     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU     8     0     3     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren     9     0     2     0
  Go audit · Reading all matching rows through Table Serv    10     1     0     0
  Go audit · Separate Commit after last query (RULE-GO-10     5     1     5     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv    10     1     0     0
  Go audit · for-loop wrapping Do (RULE-GO-04)                8     1     2     0
  Java audit · JDBC batching not configured (RULE-JV-02)      5     6     0     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            10     0     1     0
  Java audit · Spring save() in a loop (RULE-JV-03)           6     5     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       10     0     1     0
  Java audit · findById in a loop (RULE-JV-01)               11     0     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    11     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                 9     2     0     0
  Query · Keyset pagination in YQL + Go                       8     0     3     0
  Query · Primary-key design for IoT events (monotonic-PK     5     1     4     1

──────────────────────────────────────────────────────────────────────────────
Notable cells (sorted by verdict severity)
──────────────────────────────────────────────────────────────────────────────
  ! SKILL_HARMS    Frontier · Anthropic Opus 4.7             Query · Primary-key design for IoT events
  ! SKILL_HARMS    Frontier · OpenAI GPT-5.3 Codex           Core · Cloud auth without hardcoded credentials
  ! SKILL_HARMS    Laptop · OpenAI gpt-oss-20b               Core · Cloud auth without hardcoded credentials

  x INSUFFICIENT   Frontier OSS · DeepSeek v4-Pro            Core · Local Docker + Python quickstart
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Core · Onboarding — 3-minute YDB intro
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Custom retrier with time.Sleep
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · Explicit BeginTransaction
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Explicit BeginTransaction
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · External state mutation from Do
  x INSUFFICIENT   Frontier OSS · DeepSeek v4-Pro            Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Frontier · Anthropic Opus 4.7             Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Missing WithIdempotent on Do
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Missing WithIdempotent on Do
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Go audit · Non-parametrized YQL via fmt.Sprintf
  x INSUFFICIENT   Frontier OSS · DeepSeek v4-Pro            Go audit · PreferLocalDC / PreferNearestDC
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · PreferLocalDC / PreferNearestDC
  x INSUFFICIENT   Frontier OSS · Qwen3.6 Plus               Go audit · PreferLocalDC / PreferNearestDC
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · PreferNearestDC balancer
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · PreferNearestDC balancer
  x INSUFFICIENT   Frontier OSS · DeepSeek v4-Pro            Go audit · Separate Commit after last query
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · Separate Commit after last query
  x INSUFFICIENT   Frontier OSS · Moonshot Kimi K2.6         Go audit · Separate Commit after last query
  x INSUFFICIENT   Frontier OSS · Z.ai GLM 4.7               Go audit · Separate Commit after last query
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Separate Commit after last query
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · for-loop wrapping Do
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · for-loop wrapping Do
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Java audit · JPA @Version over YDB
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Java audit · deleteAllById on bulk path
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Query · Keyset pagination in YQL + Go
  x INSUFFICIENT   Frontier · Google Gemini 3.1 Pro          Query · Keyset pagination in YQL + Go
  x INSUFFICIENT   Frontier · OpenAI GPT-5.3 Codex           Query · Keyset pagination in YQL + Go
  x INSUFFICIENT   Frontier OSS · Z.ai GLM 4.7               Query · Primary-key design for IoT events
  x INSUFFICIENT   Frontier · Google Gemini 3.1 Pro          Query · Primary-key design for IoT events
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Query · Primary-key design for IoT events
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events
```

For the full per-cell breakdown (including the 48 `REDUNDANT` and 211
`SKILL_WORKS` rows), re-run
`python3 scripts/ab-compare.py --skill eval-MSx-2026-05-25T12:59:55 --bare eval-cI8-2026-05-25T13:00:02`
— the data is preserved in `~/.promptfoo/promptfoo.db` and the script
is deterministic.

## Changes since 2026-05-25 (Sonnet baseline)

The grader swap alone reshuffled the headline. **No skill, test, or
provider changes** between the two baselines in this PR.

|              | Sonnet (185-baseline) | Haiku (211-baseline) | Δ      |
|--------------|----------------------:|---------------------:|-------:|
| SKILL_WORKS  | 185 (62.3%)           | **211 (71.0%)**      | **+26**|
| REDUNDANT    | 88 (29.6%)            | 48 (16.2%)           | -40    |
| INSUFFICIENT | 22 (7.4%)             | 35 (11.8%)           | +13    |
| SKILL_HARMS  | 2 (0.7%)              | 3 (1.0%)             | +1     |
| ERROR        | 0                     | 0                    | -      |

The dominant direction is `REDUNDANT → SKILL_WORKS` (~40 cells). Under
Sonnet, many bare-control outputs were getting borderline PASSes that
masked the skill's contribution; Haiku's stricter clause-enforcement
flips those bare cells to FAIL, which moves the corresponding (skill
PASS / bare FAIL) cell into the SKILL_WORKS quadrant.

A smaller `SKILL_WORKS → INSUFFICIENT` countercurrent (~13 cells)
identifies real weak spots in skill prose — places where Sonnet was
also being lenient about the skill-loaded answer.

The pre-validation projection (`scripts/simulate-grader-swap.py`)
predicted SKILL_WORKS 205, REDUNDANT 57, INSUFFICIENT 32, SKILL_HARMS 1.
The actual rerun came in at SKILL_WORKS 211, REDUNDANT 48, INSUFFICIENT
35, SKILL_HARMS 3. The ~10-cell spread is normal model-output variance
at temperature 0 (OpenRouter back-end routing also contributes).

## Open follow-ups

- **SKILL_HARMS · `Core · Cloud auth without hardcoded credentials`
  (2 cells, new under Haiku).** Both GPT-5.3 Codex and gpt-oss-20b pass
  this test bare and fail with the skill loaded. Read both responses
  side-by-side — the cloud-auth reference may be steering them toward a
  more verbose-but-flawed shape (e.g. an outdated SDK call), while
  bare-training gives a cleaner answer.
- **SKILL_HARMS · Opus 4.7 · Query · Primary-key design IoT.** Carried
  over from the Sonnet baseline. The IoT rubric tightened recently
  (`6a6d974 tests: tighten PK design IoT rubric to require
  AUTO_PARTITIONING_* knobs`); Opus may be missing a specific knob name.
- **INSUFFICIENT cluster · Go-SDK tx-control rules.** `Interactive
  Table Service tx.CommitTx` (5 cells) and `Separate Commit after last
  query` (5 cells) fail across mid-tier providers even with the skill.
  Candidate edit: a 4–6 line diff-style Fix block showing the canonical
  multi-statement `s.Execute(... TxControl(BeginTx(...), CommitTx())
  ...)` form. (Same item as on the previous baseline — moved further
  up the priority list since the cluster is now ~10 cells.)
- **INSUFFICIENT cluster · `Query · Keyset pagination in YQL + Go`
  (3 cells, grew from 1 under Sonnet).** The long-scans reference
  landed in PR #2 but isn't anchoring tight enough across MiniMax,
  Gemini 3.1 Pro, and GPT-5.3 Codex. Worth a focused read of the three
  failing outputs to see which rubric criterion they share.
- **INSUFFICIENT cluster · `Go audit · PreferLocalDC / PreferNearestDC
  balancer` (3 cells, new cluster under Haiku).** Three frontier-OSS
  providers fail this with the skill loaded. Sonnet had been giving
  these a pass; Haiku is reading the rubric criteria literally. Inspect
  what wording the skill text uses vs. the rubric.
- **The phantom Devstral · Onboarding SKILL_HARMS from the Sonnet
  baseline did not reappear** — confirmed grader artifact. Devstral now
  shows up as INSUFFICIENT on Onboarding, which is the right verdict
  for that test/provider pair.
