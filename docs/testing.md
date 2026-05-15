# Testing skills

Goal: build a **compatibility matrix** — for each `(provider, model)`, measure how well our installable skills work when loaded into a coding-agent-style system prompt. Identifies the minimum model per vendor family that still passes.

The tool is [promptfoo](https://www.promptfoo.dev). One declarative `promptfooconfig.yaml` at the repo root drives everything.

## What this tests

Every eval runs this shape:

- **System prompt:** "You are a coding agent. Here are four YDB skills installed — full content of each SKILL.md." (See [`prompts/coding-agent.yaml`](../prompts/coding-agent.yaml).)
- **User prompt:** supplied by the test case (`tests/<skill>/<case>.yaml`).
- **Grader:** `claude-sonnet-4.6` judges each `llm-rubric` assertion against a criterion block written in plain English.

This approximates the *ceiling* per model — all skills are fully visible. A model that fails this can't work in a real runtime (Claude Code, Codex, Cursor, etc.) where the agent additionally has to decide which skill to load.

Runtime-specific behavior (how Claude Code chooses skills vs. how Codex does) is **not** tested here. That requires installing each runtime and running against it, which is a manual exercise — see the [known gap](#runtime-level-testing-known-gap) below.

## Setup

One-time:

```bash
# Endpoint root for an OpenRouter-style OpenAI-compatible provider.
# The config appends /api/v1 itself — set only the host here.
export OPENROUTER_API_BASE_URL="https://openrouter.ai"
export OPENROUTER_API_KEY="<token>"
```

promptfoo runs via `npx` — no local install needed:

```bash
npx promptfoo@latest eval         # run all tests across all providers
npx promptfoo@latest view         # open the matrix in the browser
```

For a subset (faster iteration while writing a new skill or test):

```bash
# single provider (regex match on provider id)
npx promptfoo@latest eval --filter-providers 'qwen3-coder'

# single test (regex match on the test's `description` field)
npx promptfoo@latest eval --filter-pattern 'keyset pagination'

# first N tests only
npx promptfoo@latest eval --filter-first-n 3

# combine: one test on one provider
npx promptfoo@latest eval \
  --filter-pattern 'Cloud auth' \
  --filter-providers 'anthropic/claude-sonnet-4.6'
```

Results are stored in `~/.promptfoo/` and rendered as a matrix: rows = models, columns = test cases, cells = pass/fail + grader reasoning.

## Adding a test

1. Copy an existing file under `tests/<skill>/` as a starting point — structure is `description`, `vars.user_prompt`, `assert`.
2. Write the `user_prompt` as a realistic user turn. Avoid toy examples — model size matters less on trivial prompts.
3. Write the `llm-rubric` criteria as bullet points the grader can check against the skill content. Every criterion should be something the grader can verify from the skill body alone. Do not introduce facts that aren't in any SKILL.md — the test would be impossible to pass on principle.
4. Run once with a cheap model and read the grader's reasoning. If the criteria are too loose (everything passes) or too strict (everything fails), tighten / relax them.
5. Commit once the rubric gives stable results across two runs.

Worked example — a minimal outcome test:

```yaml
description: Query · Keyset pagination in YQL + Go

vars:
  user_prompt: |
    Write a YQL query and the Go code to paginate a `users` table by
    `created_at` (Timestamp) and `id` (Uint64) — 50 rows per page.

assert:
  - type: llm-rubric
    value: |
      The response should:
      - Use keyset pagination: `WHERE (created_at, id) > ...`. Avoid `OFFSET`.
      - Declare parameters with `DECLARE` — no raw string interpolation.
      - Wrap the Go query in a session-retry scope (db.Query().Do(...)).
      Partial credit if pagination is correct but Go wrapper is missing.
```

## Adding a model

Edit `promptfooconfig.yaml`. Copy one of the existing provider rows:

```yaml
- id: openai:chat:<vendor>/<model-slug>
  label: <Human-friendly label>
  config: *openrouter
```

The `<vendor>/<model-slug>` must match what OpenRouter exposes. Check the live list at https://openrouter.ai/models.

## Reading the matrix

`npx promptfoo@latest view` opens an HTML matrix.

- **Green cell (pass)** — the grader judged the response to satisfy every criterion. Sanity-check by clicking the cell and reading the reasoning; occasionally the grader is too generous.
- **Red cell (fail)** — the grader flagged at least one criterion as unmet. Read the reasoning to see whether this is a genuine failure or a too-strict rubric.
- **Yellow / partial** — one or more criteria failed but others passed; the test opted into partial credit via the rubric wording.

Per-model summary: pass rate column on the right. This is what drives the "minimum model per family" decision.

## When to bump the model set

- A new major model ships and is available on `/openrouter`. Add a row, re-run.
- A model gets deprecated. Remove the row.
- A customer asks "does our skill work on model X?" and X is not in the matrix. Add it, commit the matrix run output to `matrix.md` (optional — see below).

## Committing matrix results

Not done by default. The matrix changes every time any skill or test changes, so committing full results would be noisy. If you want a snapshot for an external stakeholder, run `npx promptfoo@latest eval --output matrix.md --format markdown`.

## Runtime-level testing (known gap)

This setup tests models. It does not test runtimes — Claude Code / Cursor / Windsurf / Codex / Gemini CLI each have their own skill-loading mechanics (description-first routing, varying system-prompt construction, different tool sets) that can change the outcome from what the matrix shows.

Runtime-level testing requires installing each runtime and running against it with the skill installed. That is manual today:

1. Install skills into the target runtime (`./install.sh --agent=<name>`).
2. Spin up the runtime with a target model.
3. Paste a prompt from `tests/` into the runtime's chat.
4. Eye-check the response.

A non-trivial runtime-testing harness would need per-runtime drivers (subprocess calls or embedded automation). That's deferred — see [`TODO.md`](../TODO.md).

## What is NOT included

- **CI workflow.** Promptfoo runs locally against an OpenAI-compatible endpoint. CI wiring would require that endpoint to be reachable from CI and an API key provisioned as a secret — out of scope right now.
- **Cost tracking.** The matrix runs every provider × every test. With ~12 models × 12 tests × grader, expect on the order of 150–200 model calls per full run. Use `--filter-providers` / `--filter-tests` during iteration to keep the spend low.
- **Trigger-only tests.** The current layout always loads all installable skills. If you need to measure "does the model correctly pick ydb-table given only the descriptions?" — that's a second-stage rig, not built here.

## See also

- [promptfoo docs](https://www.promptfoo.dev/docs/intro) — the framework itself.
- [promptfoo OpenAI-compat provider](https://www.promptfoo.dev/docs/providers/openai/) — the provider type all our models use.
- [`promptfooconfig.yaml`](../promptfooconfig.yaml) — the matrix config.
- [`prompts/coding-agent.yaml`](../prompts/coding-agent.yaml) — the shared system prompt.
- [`docs/authoring.md`](authoring.md) — how to write a skill; conventions that tests check against.
