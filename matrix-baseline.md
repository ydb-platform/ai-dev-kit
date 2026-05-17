# Matrix baseline — 2026-05-17

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

- **9 providers** × **11 tests** = 99 cells.
- Concurrency 12. No transport errors in this run.
- Reasoning disabled only on Moonshot Kimi K2.6 — other providers reject
  the flag (`reasoning: { enabled: false }` → HTTP 400). For Qwen3.6
  35B-A3B (also a thinking model) we leave reasoning on and bump
  `max_tokens` to 8192 instead. See [`docs/testing.md`](docs/testing.md#speed-knobs).

## Provider mix

Three tiers × three models:

- **Frontier · closed:** Anthropic Opus 4.7, OpenAI GPT-5.3 Codex,
  Google Gemini 3.1 Pro (preview).
- **Frontier · open-source:** DeepSeek v4-Pro, Moonshot Kimi K2.6,
  Qwen3.6 Plus.
- **Laptop · Ollama-runnable:** OpenAI gpt-oss-20b, Mistral Devstral
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
skill eval: eval-KMp-2026-05-17T06:26:58
bare eval:  eval-Lgl-2026-05-17T06:29:42

──────────────────────────────────────────────────────────────────────────────
Headline (cells across all providers × tests)
──────────────────────────────────────────────────────────────────────────────
  + SKILL_WORKS      54  ( 54.5%)
  . REDUNDANT        44  ( 44.4%)
  x INSUFFICIENT      0  (  0.0%)
  ! SKILL_HARMS       1  (  1.0%)
  ? ERROR             0  (  0.0%)

──────────────────────────────────────────────────────────────────────────────
Per-test (aggregated across providers)
──────────────────────────────────────────────────────────────────────────────
  TEST                                                    works  redu insuf harms
  Core · Cloud auth without hardcoded credentials             2     7     0     0
  Core · Local Docker + Python quickstart                     5     4     0     0
  Core · Onboarding — 3-minute YDB intro for a newcomer       1     8     0     0
  Java audit · JDBC batching not configured (RULE-JV-02)      3     6     0     0
  Java audit · JPA @Version over YDB (RULE-JV-05)             9     0     0     0
  Java audit · Spring save() in a loop (RULE-JV-03)           6     3     0     0
  Java audit · deleteAllById on bulk path (RULE-JV-04)        6     3     0     0
  Java audit · findById in a loop (RULE-JV-01)                3     5     0     1
  Java audit · ignoring retryable JDBC exceptions (RULE-J     9     0     0     0
  Query · Converting PostgreSQL SERIAL to YQL                 9     0     0     0
  Query · Primary-key design for IoT events (monotonic-PK     1     8     0     0

──────────────────────────────────────────────────────────────────────────────
Per-cell (sorted by verdict)
──────────────────────────────────────────────────────────────────────────────
  ! SKILL_HARMS    Laptop · Qwen3.6 35B-A3B                  Java audit · findById in a loop (RULE-JV-01)
  + SKILL_WORKS    Frontier · Anthropic Opus 4.7             Core · Cloud auth without hardcoded credentia
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Core · Cloud auth without hardcoded credentia
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Core · Local Docker + Python quickstart
  + SKILL_WORKS    Frontier OSS · Moonshot Kimi K2.6         Core · Local Docker + Python quickstart
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Core · Local Docker + Python quickstart
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Core · Local Docker + Python quickstart
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Core · Local Docker + Python quickstart
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Core · Onboarding — 3-minute YDB intro for a
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · JDBC batching not configured (RU
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Java audit · JDBC batching not configured (RU
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Java audit · JDBC batching not configured (RU
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier OSS · Moonshot Kimi K2.6         Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier OSS · Qwen3.6 Plus               Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier · Anthropic Opus 4.7             Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier · Google Gemini 3.1 Pro (preview)  Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Java audit · JPA @Version over YDB (RULE-JV-0
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Frontier · Anthropic Opus 4.7             Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Java audit · Spring save() in a loop (RULE-JV
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Frontier OSS · Moonshot Kimi K2.6         Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Frontier OSS · Qwen3.6 Plus               Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Java audit · deleteAllById on bulk path (RULE
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · findById in a loop (RULE-JV-01)
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Java audit · findById in a loop (RULE-JV-01)
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Java audit · findById in a loop (RULE-JV-01)
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier OSS · Moonshot Kimi K2.6         Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier OSS · Qwen3.6 Plus               Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier · Anthropic Opus 4.7             Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier · Google Gemini 3.1 Pro (preview)  Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Java audit · ignoring retryable JDBC exceptio
  + SKILL_WORKS    Frontier OSS · DeepSeek v4-Pro            Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Frontier OSS · Moonshot Kimi K2.6         Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Frontier OSS · Qwen3.6 Plus               Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Frontier · Anthropic Opus 4.7             Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Frontier · Google Gemini 3.1 Pro (preview)  Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Frontier · OpenAI GPT-5.3 Codex           Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Laptop · OpenAI gpt-oss-20b               Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Laptop · Qwen3.6 35B-A3B                  Query · Converting PostgreSQL SERIAL to YQL
  + SKILL_WORKS    Laptop · Mistral Devstral Small           Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier OSS · DeepSeek v4-Pro            Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Frontier · OpenAI GPT-5.3 Codex           Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Laptop · OpenAI gpt-oss-20b               Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Laptop · Qwen3.6 35B-A3B                  Core · Cloud auth without hardcoded credentia
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Core · Local Docker + Python quickstart
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Core · Local Docker + Python quickstart
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Core · Local Docker + Python quickstart
  . REDUNDANT      Frontier · OpenAI GPT-5.3 Codex           Core · Local Docker + Python quickstart
  . REDUNDANT      Frontier OSS · DeepSeek v4-Pro            Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier · OpenAI GPT-5.3 Codex           Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Laptop · OpenAI gpt-oss-20b               Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Laptop · Qwen3.6 35B-A3B                  Core · Onboarding — 3-minute YDB intro for a
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Java audit · JDBC batching not configured (RU
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Java audit · JDBC batching not configured (RU
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Java audit · JDBC batching not configured (RU
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Java audit · JDBC batching not configured (RU
  . REDUNDANT      Frontier · OpenAI GPT-5.3 Codex           Java audit · JDBC batching not configured (RU
  . REDUNDANT      Laptop · Qwen3.6 35B-A3B                  Java audit · JDBC batching not configured (RU
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Java audit · Spring save() in a loop (RULE-JV
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Java audit · Spring save() in a loop (RULE-JV
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Java audit · Spring save() in a loop (RULE-JV
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Java audit · deleteAllById on bulk path (RULE
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Java audit · deleteAllById on bulk path (RULE
  . REDUNDANT      Laptop · OpenAI gpt-oss-20b               Java audit · deleteAllById on bulk path (RULE
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Java audit · findById in a loop (RULE-JV-01)
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Java audit · findById in a loop (RULE-JV-01)
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Java audit · findById in a loop (RULE-JV-01)
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Java audit · findById in a loop (RULE-JV-01)
  . REDUNDANT      Laptop · Mistral Devstral Small           Java audit · findById in a loop (RULE-JV-01)
  . REDUNDANT      Frontier OSS · DeepSeek v4-Pro            Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier OSS · Moonshot Kimi K2.6         Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier OSS · Qwen3.6 Plus               Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier · Anthropic Opus 4.7             Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier · Google Gemini 3.1 Pro (preview)  Query · Primary-key design for IoT events (mo
  . REDUNDANT      Frontier · OpenAI GPT-5.3 Codex           Query · Primary-key design for IoT events (mo
  . REDUNDANT      Laptop · OpenAI gpt-oss-20b               Query · Primary-key design for IoT events (mo
  . REDUNDANT      Laptop · Qwen3.6 35B-A3B                  Query · Primary-key design for IoT events (mo
```

## Changes since 2026-05-16

- Swapped providers: Gemini 2.5 Pro → 3.1 Pro (preview); Qwen3 Coder
  Plus → Qwen3.6 Plus; Qwen3 Coder 30B-A3B → Qwen3.6 35B-A3B. Bumped
  `max_tokens` to 8192 on Qwen3.6 35B-A3B (reasoning model — 2048 was
  eaten by the thinking budget, answers came back truncated).
- INSUFFICIENT cleared: was 2 (Gemini 2.5 / RULE-JV-06, Qwen3 30B /
  PK design IoT) → now 0. The PK design IoT cell on the new Qwen3.6
  flipped to REDUNDANT (model already knows); Gemini 3.1 picked up
  RULE-JV-06.
- SKILL_WORKS: 58 → 54. The four lost cells didn't regress to FAIL —
  they moved to REDUNDANT because the newer models know more. Frontier
  ceiling crept up; the laptop tier is where the skill still earns its
  keep.

## Open follow-ups

- **SKILL_HARMS · Qwen3.6 35B-A3B · RULE-JV-01.** The model's actual
  response cites the rule and gives the correct `findAllById` fix. The
  failure is a grader artifact — Sonnet-4.6 returned non-JSON for this
  cell ("Could not extract JSON from llm-rubric response"). Phantom,
  not a real regression. Will probably disappear on re-run; worth
  re-checking before treating it as load-bearing signal.
