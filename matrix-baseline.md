# Matrix baseline — 2026-05-25

Snapshot of the A/B compatibility matrix at a known-good point. Future
edits to skills should be compared against this — a meaningful change
should move cells from `REDUNDANT` / `INSUFFICIENT` toward `SKILL_WORKS`
without regressing `SKILL_WORKS` cells.

## How this was produced

```bash
export OPENROUTER_API_KEY="..."
npx promptfoo@latest eval                                # skill loaded
npx promptfoo@latest eval -c promptfooconfig.bare.yaml   # bare control
python3 scripts/ab-compare.py
```

This run filled budget-induced gaps via two follow-on retries with
`--filter-errors-only`, then merged the results in `ab-compare.py` via
the new `--skill-retry` / `--bare-retry` overlay flags (the retry
verdicts replace base-eval cells whose `failureReason == 2`, i.e.
transport / credit errors). The merged input is what produced the
snapshot below.

- **11 providers** × **27 tests** = 297 cells.
- Concurrency 12. **No transport / credit errors after the overlay** —
  the initial parallel runs spent the $30 monthly OpenRouter cap mid-way
  and produced 87 ERROR cells. Topping up the key and re-running with
  `--filter-errors-only` recovered all 87 cells; the snapshot below is
  the clean, complete state.
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
  Qwen3.6 Plus, **Z.ai GLM 4.7** (new), **MiniMax M2.7** (new).
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
skill eval: eval-ptt-2026-05-25T10:51:38  + retry eval-d2m-2026-05-25T11:12:55
bare eval:  eval-amm-2026-05-25T10:51:40  + retry eval-V7j-2026-05-25T11:13:03

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS     185  ( 62.3%)
  . REDUNDANT        88  ( 29.6%)
  x INSUFFICIENT     22  (  7.4%)
  ! SKILL_HARMS       2  (  0.7%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  Core · Cloud auth without hardcoded credentials             2     9     0     0
  Core · Local Docker + Python quickstart                     7     4     0     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       1     9     0     1
  Go audit · Custom retrier with time.Sleep (RULE-GO-05)      4     7     0     0
  Go audit · Explicit BeginTransaction before first query     9     0     2     0
  Go audit · External state mutation from Do retry closur     4     7     0     0
  Go audit · Interactive Table Service `tx.CommitTx` as a     7     0     4     0
  Go audit · Missing WithIdempotent on Do (RULE-GO-03)        7     4     0     0
  Go audit · Nested Do call (RULE-GO-06)                      1    10     0     0
  Go audit · Non-interactive DoTx auto-commit without `qu    10     0     1     0
  Go audit · Non-interactive DoTx without `ydb.WithLazyTx    10     0     1     0
  Go audit · Non-parametrized YQL via fmt.Sprintf (RULE-G    10     0     1     0
  Go audit · PreferLocalDC / PreferNearestDC balancer (RU    11     0     0     0
  Go audit · PreferNearestDC balancer (RULE-GO-08, curren     9     1     1     0
  Go audit · Reading all matching rows through Table Serv    11     0     0     0
  Go audit · Separate Commit after last query (RULE-GO-10     7     0     4     0
  Go audit · `ydb.WithIgnoreTruncated` masking Table Serv     4     7     0     0
  Go audit · for-loop wrapping Do (RULE-GO-04)                5     5     1     0
  Java audit · JDBC batching not configured (RULE-JV-02)      2     9     0     0
  Java audit · JPA @Version over YDB (RULE-JV-05)            11     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           8     3     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)       10     0     1     0
  Java audit · findById in a loop (RULE-JV-01)                4     7     0     0
  Java audit · ignoring retryable JDBC exceptions (RULE-J    10     0     1     0
  Query · Converting PostgreSQL SERIAL to YQL                10     1     0     0
  Query · Keyset pagination in YQL + Go                       5     5     1     0
  Query · Primary-key design for IoT events (monotonic-PK     6     0     4     1

──────────────────────────────────────────────────────────────────────────────
Notable cells (sorted by verdict severity)
──────────────────────────────────────────────────────────────────────────────
  ! SKILL_HARMS    Laptop · Mistral Devstral Small           Core · Onboarding — 3-minute YDB intro
  ! SKILL_HARMS    Frontier · Anthropic Opus 4.7             Query · Primary-key design for IoT events

  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Explicit BeginTransaction
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Explicit BeginTransaction
  x INSUFFICIENT   Frontier OSS · DeepSeek v4-Pro            Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Frontier OSS · Moonshot Kimi K2.6         Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Interactive Table Service `tx.CommitTx`
  x INSUFFICIENT   Laptop · OpenAI gpt-oss-20b               Go audit · Non-interactive DoTx auto-commit
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Non-interactive DoTx without `ydb.WithLazyTx`
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Non-parametrized YQL via fmt.Sprintf
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Go audit · PreferNearestDC balancer
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · Separate Commit after last query
  x INSUFFICIENT   Frontier OSS · Z.ai GLM 4.7               Go audit · Separate Commit after last query
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Go audit · Separate Commit after last query
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Go audit · Separate Commit after last query
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Go audit · for-loop wrapping Do (RULE-GO-04)
  x INSUFFICIENT   Laptop · Mistral Devstral Small           Java audit · deleteAllById on bulk path
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Java audit · ignoring retryable JDBC exceptions
  x INSUFFICIENT   Frontier OSS · Z.ai GLM 4.7               Query · Keyset pagination in YQL + Go
  x INSUFFICIENT   Frontier OSS · MiniMax M2.7               Query · Primary-key design for IoT events
  x INSUFFICIENT   Frontier OSS · Qwen3.6 Plus               Query · Primary-key design for IoT events
  x INSUFFICIENT   Frontier OSS · Z.ai GLM 4.7               Query · Primary-key design for IoT events
  x INSUFFICIENT   Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events
```

For the full per-cell breakdown (including the 88 `REDUNDANT` and 185
`SKILL_WORKS` rows), re-run `python3 scripts/ab-compare.py --skill … --bare …
--skill-retry … --bare-retry …` with the eval IDs above; the data is
preserved in `~/.promptfoo/promptfoo.db` and the script is deterministic.

## Changes since 2026-05-17

- **Provider mix expanded 9 → 11.** Added two enterprise-OSS rows on
  the Frontier OSS tier: `z-ai/glm-4.7` and `minimax/minimax-m2.7`
  (both used at the company, both ~$0.0000003–4/tok input). No
  removals.
- **Test set expanded 11 → 27.** Most of the growth is the Go-SDK audit
  suite (`tests/ydb-table/go-rule-go-*.yaml`, 15 tests) that landed in
  `b0fe364` after the previous baseline, plus one new query test
  `tests/ydb-table/keyset-pagination.yaml` added in this PR.
- **Cell count 99 → 297.** Headline shifted accordingly:
  - SKILL_WORKS  54 → 185  (54.5% → 62.3%) — the new Go audit tests
    are heavily skill-load-bearing; most cells flip PASS only with the
    rule body loaded.
  - REDUNDANT    44 → 88   (44.4% → 29.6%) — same providers, more
    tests; the redundant-by-training share dropped because the new
    tests cover SDK-API specifics that even frontier models don't
    recall correctly without the skill.
  - INSUFFICIENT  0 → 22   (0% → 7.4%) — new ground. Concentrated on
    Go-SDK-internal tests (Interactive Table Service `tx.CommitTx`,
    Separate Commit, Explicit BeginTransaction) where smaller models
    miss the rule even with the skill text in front of them. These
    are the cells where the rule prose needs tightening or examples
    sharpening — see Open follow-ups.
  - SKILL_HARMS   1 → 2    (1.0% → 0.7%) — both new, both worth
    inspecting (see Open follow-ups).
  - ERROR         0 → 0    (clean after retry overlay).

## Open follow-ups

- **SKILL_HARMS · Mistral Devstral Small · Core · Onboarding.** Skill
  loaded made the model fail an Onboarding test that bare passes. Most
  likely a grader-formatting artifact (this exact pair was clean on a
  manual re-check earlier in the day) but worth re-running once to
  confirm not load-bearing.
- **SKILL_HARMS · Anthropic Opus 4.7 · Query · Primary-key design IoT.**
  Frontier model regressed when the schema rule was loaded. The IoT
  rubric tightened recently (`6a6d974 tests: tighten PK design IoT
  rubric to require AUTO_PARTITIONING_* knobs`) — Opus may be missing
  a specific knob name. Inspect Opus's response and compare to rubric.
- **INSUFFICIENT cluster on Go-SDK transaction-control tests.** Four
  cells fail both with and without the skill for Interactive Table
  Service `tx.CommitTx`, four more for Separate Commit. Suggests
  RULE-GO-10 / RULE-GO-10b prose isn't anchoring the fix shape clearly
  enough for laptop/mid-tier models. Candidate edit: a 4–6 line
  diff-style Fix block showing the canonical multi-statement
  `s.Execute(... TxControl(BeginTx(...), CommitTx()) ...)` form.
- **INSUFFICIENT · Z.ai GLM 4.7 · Query · Keyset pagination.** Single
  cell where the new long-scans reference doesn't land. GLM 4.7
  produced keyset shape but missed one of the typed-parameter / `Do`
  wrapper / `WithIdempotent` criteria. Worth a focused re-check on
  this model after the grader-swap follow-up PR lands (Haiku's
  stricter JSON adherence may shift the verdict).
- **INSUFFICIENT cluster on Query · Primary-key design for IoT.** Four
  Frontier-OSS + Laptop providers fail this even with the skill — same
  recent-rubric-tightening as the Opus SKILL_HARMS row above. Either
  loosen the rubric (acknowledge `AUTO_PARTITIONING_*` is one of
  several valid knob sets) or strengthen the skill text with the
  exact knob list.
