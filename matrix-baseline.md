# Matrix baseline — 2026-05-26 (Haiku grader, PR #4)

Snapshot of the A/B compatibility matrix after ai-dev-kit#4 (`ydb-core`
balancing references + RULE-GO-11). Future edits to skills should be
compared against this — a meaningful change should move cells from
`REDUNDANT` / `INSUFFICIENT` toward `SKILL_WORKS` without regressing
`SKILL_WORKS` cells.

> **Snapshot scope (2026-05-26, this PR).** Same grader
> (`anthropic/claude-haiku-4.5`), same provider mix, same tests as the
> 211-baseline. Only delta: `ydb-core` gained `references/balancing.md`,
> `references/session-lifecycle.md`, `references/embed/go.md`, and
> `rules/embed/go.md` (RULE-GO-11), all wired into the eval system
> prompt via `promptfooconfig.yaml`. Bare control re-uses
> `eval-cI8-2026-05-25T13:00:02` (bare config unchanged by this PR;
> all its cells would have been cache hits anyway).

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
npx promptfoo@latest eval                                # skill loaded (new ID below)
# bare control reused from the 211-baseline — bare config unchanged.
python3 scripts/ab-compare.py --skill <new-id> --bare eval-cI8-2026-05-25T13:00:02
```

- **11 providers** × **27 tests** = 297 cells per side.
- Concurrency 12. **No transport / credit errors** in the final pass —
  one partial pass earlier in the day hit the OpenRouter monthly cap
  (281 cells / 297 erroring); after a key top-up the rerun completed
  in 9m 21s with 0 errors.
- Reasoning disabled only on Moonshot Kimi K2.6 — other providers reject
  the flag. For Qwen3.6 35B-A3B and OpenAI gpt-oss-20b we leave
  reasoning on and bump `max_tokens` to 8192. See
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
skill eval: eval-lQE-2026-05-26T02:41:54
bare eval:  eval-cI8-2026-05-25T13:00:02
grader:     anthropic/claude-haiku-4.5

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     219  ( 73.7%)
  . REDUNDANT        51  ( 17.2%)
  x INSUFFICIENT     27  (  9.1%)
  ! SKILL_HARMS       0  (  0.0%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  Core · Cloud auth without hardcoded credentials             3     8     0     0
  Core · Local Docker + Python quickstart                     8     3     0     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       7     4     0     0
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      5     6     0     0
  Go audit · Explicit BeginTransaction before first query     9     1     1     0
  Go audit · External state mutation from Do retry closur     9     1     1     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     5     0     6     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        8     1     2     0
  Go audit · Nested Do call (RULE-GO-06)                      6     5     0     0
  Go audit · Non-interactive DoTx auto-commit without `qu    11     0     0     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx    10     0     1     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G     6     3     2     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU    10     0     1     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren    10     0     1     0
  Go audit · Reading all matching rows through Table Serv     8     1     2     0
  Go audit · Separate Commit after last query (RULE-GO-10     8     1     2     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv    10     1     0     0
  Go audit · for-loop wrapping Do (RULE-GO-04)                9     1     1     0
  Java audit · JDBC batching not configured (RULE-JV-02)      4     6     1     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            11     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           6     5     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       10     0     1     0
  Java audit · findById in a loop (RULE-JV-01)               11     0     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    11     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                 9     2     0     0
  Query · Keyset pagination in YQL + Go                      10     0     1     0
  Query · Primary-key design for IoT events (monotonic-PK     5     2     4     0

──────────────────────────────────────────────────────────────────────────────
INSUFFICIENT cells (the 27)
──────────────────────────────────────────────────────────────────────────────
  Laptop · OpenAI gpt-oss-20b               Go audit · Explicit BeginTransaction
  Laptop · Mistral Devstral Small           Go audit · External state mutation from Do
  Frontier OSS · MiniMax M2.7               Go audit · Interactive Table Service tx.CommitTx
  Frontier OSS · Moonshot Kimi K2.6         Go audit · Interactive Table Service tx.CommitTx
  Frontier OSS · Z.ai GLM 4.7               Go audit · Interactive Table Service tx.CommitTx
  Laptop · Mistral Devstral Small           Go audit · Interactive Table Service tx.CommitTx
  Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service tx.CommitTx
  Laptop · Qwen3.6 35B-A3B                  Go audit · Interactive Table Service tx.CommitTx
  Frontier OSS · MiniMax M2.7               Go audit · Missing WithIdempotent on Do
  Laptop · OpenAI gpt-oss-20b               Go audit · Missing WithIdempotent on Do
  Frontier OSS · MiniMax M2.7               Go audit · Non-interactive DoTx without WithLazyTx
  Frontier OSS · MiniMax M2.7               Go audit · Non-parametrized YQL via fmt.Sprintf
  Laptop · Mistral Devstral Small           Go audit · Non-parametrized YQL via fmt.Sprintf
  Frontier OSS · DeepSeek v4-Pro            Go audit · PreferLocalDC / PreferNearestDC
  Laptop · Mistral Devstral Small           Go audit · PreferNearestDC balancer
  Frontier · Google Gemini 3.1 Pro          Go audit · Reading all matching rows
  Laptop · Mistral Devstral Small           Go audit · Reading all matching rows
  Laptop · Mistral Devstral Small           Go audit · Separate Commit after last query
  Laptop · Qwen3.6 35B-A3B                  Go audit · Separate Commit after last query
  Laptop · Mistral Devstral Small           Go audit · for-loop wrapping Do
  Laptop · Mistral Devstral Small           Java audit · JDBC batching not configured
  Laptop · Mistral Devstral Small           Java audit · deleteAllById on bulk path
  Frontier · Google Gemini 3.1 Pro          Query · Keyset pagination in YQL + Go
  Frontier OSS · Z.ai GLM 4.7               Query · Primary-key design for IoT events
  Laptop · Mistral Devstral Small           Query · Primary-key design for IoT events
  Laptop · OpenAI gpt-oss-20b               Query · Primary-key design for IoT events
  Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events
```

For the full per-cell breakdown (including the 51 `REDUNDANT` and 219
`SKILL_WORKS` rows), re-run
`python3 scripts/ab-compare.py --skill eval-lQE-2026-05-26T02:41:54 --bare eval-cI8-2026-05-25T13:00:02`
— the data is preserved in `~/.promptfoo/promptfoo.db` and the script
is deterministic.

## Changes since 2026-05-25 (211-baseline, pre-PR #4)

PR #4 lands `ydb-core/references/balancing.md`,
`references/session-lifecycle.md`, `references/embed/go.md`, and
`rules/embed/go.md` (RULE-GO-11). No grader / provider / test changes.

|              | Pre-PR #4 (211-baseline) | PR #4 (219-baseline) | Δ      |
|--------------|------------------------:|---------------------:|-------:|
| SKILL_WORKS  | 211 (71.0%)             | **219 (73.7%)**      | **+8** |
| REDUNDANT    | 48 (16.2%)              | 51 (17.2%)           | +3     |
| INSUFFICIENT | 35 (11.8%)              | **27 (9.1%)**        | **-8** |
| SKILL_HARMS  | 3 (1.0%)                | **0 (0.0%)**         | **-3** |
| ERROR        | 0                       | 0                    | -      |

### Per-cluster movement

Targeted by PR #4:
- **`Go audit · PreferLocalDC / PreferNearestDC`** — `8/0/3/0` → `10/0/1/0` (+2 SKILL_WORKS, −2 INSUFFICIENT).
- **`Go audit · PreferNearestDC balancer`** — `9/0/2/0` → `10/0/1/0` (+1 SKILL_WORKS, −1 INSUFFICIENT).

Bonus wins (probably from `references/session-lifecycle.md` + denser
balancing prose pulling related Go-audit reasoning along):
- **`Query · Keyset pagination`** — `8/0/3/0` → `10/0/1/0` (+2 SKILL_WORKS, −2 INSUFFICIENT). The long-scans reference from PR #2 finally anchors with the new context.
- **`Go audit · Separate Commit after last query`** — `5/1/5/0` → `8/1/2/0` (+3 SKILL_WORKS, −3 INSUFFICIENT).
- **`Core · Cloud auth without hardcoded credentials`** — `3/6/0/2` → `3/8/0/0`. Both SKILL_HARMS cells (GPT-5.3 Codex, gpt-oss-20b) recovered; the auth-confusion theory from the 211-baseline open follow-ups didn't reproduce.
- **`Query · Primary-key design for IoT events`** — `5/1/4/1` → `5/2/4/0`. The Opus SKILL_HARMS recovered.

Light regressions:
- **`Go audit · Reading all matching rows`** — `10/1/0/0` → `8/1/2/0` (−2 SKILL_WORKS into INSUFFICIENT on Gemini 3.1 Pro and Mistral Devstral). Within normal temperature variance; worth re-running once to confirm before treating as a regression.
- **`Go audit · Non-interactive DoTx without WithLazyTx`** — `11/0/0/0` → `10/0/1/0` (−1 cell on MiniMax). Same caveat — small enough to be noise.
- **`Go audit · Interactive tx.CommitTx`** — `6/0/5/0` → `5/0/6/0` (−1 on MiniMax). Cluster was already on the priority list.

The headline `−3 SKILL_HARMS → 0` is the cleanest signal: this matrix
has no cells where the skill confused the model relative to bare. That's
a first for this baseline.

## Open follow-ups

- **INSUFFICIENT cluster · Go-SDK tx-control rules.** `Interactive Table
  Service tx.CommitTx` (6 cells, up 1 from 5) and `Separate Commit after
  last query` (2 cells, down 3 from 5). The cluster shrank by 2 net but
  `tx.CommitTx` ticked up — same proposed fix as before: a diff-style
  Fix block showing canonical multi-statement `s.Execute(... TxControl(
  BeginTx(...), CommitTx()) ...)`. Worth pairing with the rule's
  test-prompt to see if the prompt itself is steering models past
  whichever wording the rule uses.
- **INSUFFICIENT cluster · `Query · Primary-key design for IoT events`
  (4 cells, unchanged).** Same Z.ai GLM 4.7 + 3 laptop providers.
  Carries over from the 211-baseline. Worth reading the four failing
  outputs side-by-side; likely the AUTO_PARTITIONING_* knob enumeration
  isn't landing on these specific models.
- **INSUFFICIENT cluster · Mistral Devstral Small (9 cells out of 27).**
  Devstral concentrates a third of all remaining INSUFFICIENT cells.
  Looks like a model-capability ceiling rather than a content gap;
  re-check by re-running just the Devstral row to rule out per-run
  variance.
- **Single-cell regressions worth a second run before treating as real:**
  `Reading all matching rows` (2 cells), `Non-interactive DoTx without
  WithLazyTx` (1 cell on MiniMax). All from one matrix pass; rerun
  with `--filter-providers 'MiniMax|Gemini|Mistral'` to confirm.
