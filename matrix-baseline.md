# Matrix baseline — 2026-06-02 (Haiku grader, PR #4 final state)

Snapshot of the A/B compatibility matrix on the final pre-merge state of
ai-dev-kit#4 (`ydb-core` balancing references + `RULE-GO-11` + bot-review
fixes). Future edits to skills should be compared against this — a
meaningful change should move cells from `REDUNDANT` / `INSUFFICIENT`
toward `SKILL_WORKS` without regressing `SKILL_WORKS` cells.

> **Snapshot scope (2026-06-02, this refresh).** Same grader
> (`anthropic/claude-haiku-4.5`), same tests as the 219-baseline.
> Two deltas vs the prior refresh: (1) the four small prose edits in
> `references/session-lifecycle.md` + `references/balancing.md` +
> `references/embed/go.md` (uncited 1000-cap + 2/3 formula softened,
> `/.metadata` warmup path dropped, cross-skill link replaced with
> prose, "Per-SDK" → "Go SDK"); (2) `mistralai/devstral-small` was
> deregistered on OpenRouter — swapped to `mistralai/mistral-small-2603`
> in both `promptfooconfig.yaml` and `promptfooconfig.bare.yaml`. The
> Mistral row's 27 cells thus reflect a different model; the rest of
> the matrix is content-only delta.

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
npx promptfoo@latest eval                                # skill loaded
npx promptfoo@latest eval -c promptfooconfig.bare.yaml   # bare control
# Bare hit a mid-run credit wall (37 cells erroring); recovered with:
npx promptfoo@latest eval -c promptfooconfig.bare.yaml \
    --filter-errors-only eval-cAl-2026-06-02T12:04:11
python3 scripts/ab-compare.py \
    --skill eval-SmQ-2026-06-02T11:58:02 \
    --bare  eval-cAl-2026-06-02T12:04:11 \
    --bare-retry eval-GXC-2026-06-02T12:17:10
```

- **11 providers** × **27 tests** = 297 cells per side.
- Concurrency 12. Skill side completed cleanly in 5m 54s. Bare side
  hit a credit wall at 260/297 cells; the `--filter-errors-only` retry
  (added in PR #2) absorbed the remaining 37 into the same baseline via
  `--bare-retry` overlay.
- Reasoning disabled only on Moonshot Kimi K2.6 — other providers reject
  the flag. Qwen3.6 35B-A3B and OpenAI gpt-oss-20b keep reasoning on
  with `max_tokens` bumped to 8192. See
  [`docs/testing.md`](docs/testing.md#speed-knobs).

## Provider mix

Three tiers:

- **Frontier · closed** (3): Anthropic Opus 4.7, OpenAI GPT-5.3 Codex,
  Google Gemini 3.1 Pro (preview).
- **Frontier · open-source** (5): DeepSeek v4-Pro, Moonshot Kimi K2.6,
  Qwen3.6 Plus, Z.ai GLM 4.7, MiniMax M2.7.
- **Laptop · Ollama-runnable** (3): OpenAI gpt-oss-20b, **Mistral Small
  2603** (replaces Devstral as of 2026-06-02), Qwen3.6 35B-A3B.

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
skill eval: eval-SmQ-2026-06-02T11:58:02
bare eval:  eval-cAl-2026-06-02T12:04:11 + retry eval-GXC-2026-06-02T12:17:10
grader:     anthropic/claude-haiku-4.5

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     221  ( 74.4%)
  . REDUNDANT        50  ( 16.8%)
  x INSUFFICIENT     25  (  8.4%)
  ! SKILL_HARMS       1  (  0.3%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  Core · Cloud auth without hardcoded credentials             4     7     0     0
  Core · Local Docker + Python quickstart                     6     3     2     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       8     3     0     0
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      5     6     0     0
  Go audit · Explicit BeginTransaction before first query    10     0     1     0
  Go audit · External state mutation from Do retry closur    11     0     0     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     6     0     5     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        8     3     0     0
  Go audit · Nested Do call (RULE-GO-06)                      2     8     0     1
  Go audit · Non-interactive DoTx auto-commit without `qu    10     0     1     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx     8     0     3     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G     9     1     1     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU    10     0     1     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren    11     0     0     0
  Go audit · Reading all matching rows through Table Serv    10     0     1     0
  Go audit · Separate Commit after last query (RULE-GO-10     7     0     4     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv    10     0     1     0
  Go audit · for-loop wrapping Do (RULE-GO-04)                8     2     1     0
  Java audit · JDBC batching not configured (RULE-JV-02)      4     7     0     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            11     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           6     5     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       11     0     0     0
  Java audit · findById in a loop (RULE-JV-01)               11     0     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    11     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                10     1     0     0
  Query · Keyset pagination in YQL + Go                       8     1     2     0
  Query · Primary-key design for IoT events (monotonic-PK     6     3     2     0

──────────────────────────────────────────────────────────────────────────────
SKILL_HARMS + INSUFFICIENT cells
──────────────────────────────────────────────────────────────────────────────
  ! SKILL_HARMS    Frontier · Google Gemini 3.1 Pro          Go audit · Nested Do call (RULE-GO-06)
                                                             — new this run; was REDUNDANT in eval-lQE.
                                                             Likely temperature variance.

  x INSUFFICIENT (25)
  Frontier OSS · Z.ai GLM 4.7               Core · Local Docker + Python quickstart
  Frontier · OpenAI GPT-5.3 Codex           Core · Local Docker + Python quickstart
  Laptop · OpenAI gpt-oss-20b               Go audit · Explicit BeginTransaction
  Frontier OSS · DeepSeek v4-Pro            Go audit · Interactive Table Service `tx.CommitTx`
  Frontier OSS · Moonshot Kimi K2.6         Go audit · Interactive Table Service `tx.CommitTx`
  Frontier OSS · Z.ai GLM 4.7               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · Mistral Small 2603               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service `tx.CommitTx`
  Laptop · OpenAI gpt-oss-20b               Go audit · Non-interactive DoTx auto-commit
  Frontier OSS · DeepSeek v4-Pro            Go audit · Non-interactive DoTx without WithLazyTx
  Frontier OSS · Z.ai GLM 4.7               Go audit · Non-interactive DoTx without WithLazyTx
  Laptop · Mistral Small 2603               Go audit · Non-interactive DoTx without WithLazyTx
  Laptop · Mistral Small 2603               Go audit · Non-parametrized YQL via fmt.Sprintf
  Frontier OSS · MiniMax M2.7               Go audit · PreferLocalDC / PreferNearestDC
  Laptop · Qwen3.6 35B-A3B                  Go audit · Reading all matching rows
  Frontier OSS · Qwen3.6 Plus               Go audit · Separate Commit after last query
  Laptop · Mistral Small 2603               Go audit · Separate Commit after last query
  Laptop · OpenAI gpt-oss-20b               Go audit · Separate Commit after last query
  Laptop · Qwen3.6 35B-A3B                  Go audit · Separate Commit after last query
  Frontier · Google Gemini 3.1 Pro          Go audit · `ydb.WithIgnoreTruncated` masking
  Frontier OSS · MiniMax M2.7               Go audit · for-loop wrapping Do
  Frontier OSS · DeepSeek v4-Pro            Query · Keyset pagination in YQL + Go
  Frontier · Google Gemini 3.1 Pro          Query · Keyset pagination in YQL + Go
  Frontier OSS · MiniMax M2.7               Query · Primary-key design for IoT events
  Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events
```

For the full per-cell breakdown (including the 50 `REDUNDANT` and 221
`SKILL_WORKS` rows), re-run
`python3 scripts/ab-compare.py --skill eval-SmQ-2026-06-02T11:58:02 --bare eval-cAl-2026-06-02T12:04:11 --bare-retry eval-GXC-2026-06-02T12:17:10`
— the data is preserved in `~/.promptfoo/promptfoo.db` and the script
is deterministic.

## Changes since 2026-05-26 (eval-lQE / 219-baseline)

|              | eval-lQE (219-baseline) | This refresh   | Δ      |
|--------------|------------------------:|---------------:|-------:|
| SKILL_WORKS  | 219 (73.7%)             | **221 (74.4%)**| **+2** |
| REDUNDANT    | 51 (17.2%)              | 50 (16.8%)     | -1     |
| INSUFFICIENT | 27 (9.1%)               | **25 (8.4%)**  | **-2** |
| SKILL_HARMS  | 0 (0.0%)                | 1 (0.3%)       | +1     |
| ERROR        | 0                       | 0              | -      |

Mild positive drift, well inside temperature variance + the two changes
listed above (prose softening, Mistral provider swap). The single new
`SKILL_HARMS` (Gemini 3.1 Pro · Nested Do call) was `REDUNDANT` in
eval-lQE; it's the kind of borderline-pass cell that flips on rerun —
likely noise, but flagged in Open follow-ups in case it sticks.

### Notable per-cluster movement

Bonus / regressions vs the 219-baseline:
- `PreferNearestDC` cluster fully consolidated: 10/0/1 → **11/0/0**.
- `External state mutation` (RULE-GO-02): 9/1/1 → **11/0/0**.
- `Reading all matching rows`: 8/1/2 → 10/0/1.
- `Missing WithIdempotent on Do`: 8/1/2 → 8/3/0.
- `Nested Do call`: 6/5/0 → 2/8/1 (more REDUNDANT, one new SKILL_HARMS).
- `for-loop wrapping Do`: 9/1/1 → 8/2/1.

## Open follow-ups

- **SKILL_HARMS · Gemini 3.1 Pro · Nested Do call (RULE-GO-06)** (new).
  Was REDUNDANT in eval-lQE; the bare-side regenerated this time (cache
  invalidated by the Mistral row swap), and Gemini's bare answer
  improved while the skill-loaded answer didn't. Worth a side-by-side
  read of the two outputs to confirm whether the skill content steers
  Gemini wrong on this rule.
- **INSUFFICIENT cluster · Go-SDK tx-control rules.** `Interactive Table
  Service tx.CommitTx` (5 cells) and `Separate Commit after last query`
  (4 cells). Cluster shrank by 1 net since eval-lQE but the
  `tx.CommitTx` half is sticky — same proposed fix as before: a
  diff-style Fix block showing canonical multi-statement
  `s.Execute(... TxControl(BeginTx(...), CommitTx()) ...)`.
- **INSUFFICIENT cluster · `Query · Primary-key design for IoT events`
  (2 cells)** — MiniMax + Qwen3.6 35B-A3B. Cluster halved (was 4).
  Worth a focused read once Open follow-up above is resolved.
- **`Core · Local Docker + Python quickstart` regression** — 8/3/0 →
  6/3/2 (-2 SKILL_WORKS, +2 INSUFFICIENT on GLM 4.7 + GPT-5.3 Codex).
  Likely temperature variance; re-check with `--filter-providers 'Z.ai|GPT-5.3'`
  before treating as real.
- **Mistral Small 2603 baseline established.** Devstral's 6
  INSUFFICIENT cells from eval-lQE → 4 cells now under Mistral 2603
  (`tx.CommitTx`, `DoTx without WithLazyTx`, `Non-parametrized YQL`,
  `Separate Commit`). The two providers can't be compared directly
  (different model), but Mistral 2603 looks roughly comparable in
  capability for these tests.
