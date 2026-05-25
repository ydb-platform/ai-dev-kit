#!/usr/bin/env python3
"""Pre-validate a grader swap by re-grading existing eval outputs.

For each (provider, test) cell in a promptfoo eval export, sends the
exact same rubricPrompt + user_prompt + model_output + rubric to a
candidate grader model and compares pass/fail to the stored verdict.

Used before swapping `defaultTest.options.provider` in promptfooconfig:
if Haiku agrees with Sonnet on >=95% of cells (no systematic skew on
either direction), the swap is safe and we can save ~10× on grader
spend. If agreement is lower, dig into disagreement cells before
committing.

Usage:
  OPENROUTER_API_KEY=... python3 scripts/grader-agreement.py \\
    --eval eval-ptt-2026-05-25T10:51:38 \\
    --eval eval-d2m-2026-05-25T11:12:55 \\
    --eval eval-amm-2026-05-25T10:51:40 \\
    --eval eval-V7j-2026-05-25T11:13:03 \\
    --candidate anthropic/claude-haiku-4.5 \\
    --cache .grader-agreement-cache.json

The cache makes retries free — re-runs only hit the API for
(eval, cell, candidate) tuples not yet stored. Delete the cache to
force a full re-grade.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import urllib.request
import urllib.error

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Mirrors promptfooconfig.yaml `defaultTest.options.rubricPrompt`.
# Kept in sync manually — if the yaml template changes, update here.
RUBRIC_PROMPT_TEMPLATE = """\
Grade whether an AI assistant's response substantively addressed a
user's YDB question and satisfied the rubric criteria.

USER PROMPT:
{user_prompt}

ASSISTANT RESPONSE:
{output}

RUBRIC:
{rubric}

Rules:
- Generic "I'm ready to help" greetings, empty refusals, requests for
  clarification when the user already gave enough detail, or answers to
  a different question → FAIL.
- Partial but substantive answers that miss a minor criterion → may PASS
  with score < 1.
- A correct response must clearly attempt to satisfy the rubric's key
  criteria, grounded in the loaded skill content.

Reply with ONE line — a single JSON object, no code fence, no prose:
{{"pass": true|false, "score": 0.0, "reason": "…"}}
"""


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return res.stdout


def export_eval(eval_id: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    run(["npx", "--yes", "promptfoo@latest", "export", "eval", eval_id, "--output", path])
    with open(path) as fh:
        return json.load(fh)


def call_grader(model: str, prompt_text: str, api_key: str, max_retries: int = 4) -> dict:
    """Call the candidate grader with the rendered rubricPrompt.

    Returns {"pass": bool, "score": float, "reason": str, "raw": str}.
    On parse failure, "pass" is None and "raw" holds the model's reply.
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(payload).encode()
    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(OPENROUTER_URL, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"].strip()
            return parse_grader_reply(content)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return {"pass": None, "score": None, "reason": last_err, "raw": ""}
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
        except (KeyError, json.JSONDecodeError, IndexError) as e:
            return {"pass": None, "score": None, "reason": f"shape: {e}", "raw": str(data)[:200]}
    return {"pass": None, "score": None, "reason": f"giving up: {last_err}", "raw": ""}


def parse_grader_reply(content: str) -> dict:
    """Extract {pass, score, reason} from the model's reply.

    The rubricPrompt asks for a single-line JSON. Haiku sometimes
    fences it or adds prose; be lenient.
    """
    # Strip code fences if present.
    m = re.search(r"\{[^{}]*\"pass\"[^{}]*\}", content)
    if not m:
        return {"pass": None, "score": None, "reason": "no JSON object found", "raw": content[:200]}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"pass": None, "score": None, "reason": "JSON parse error", "raw": content[:200]}
    return {
        "pass": bool(obj.get("pass")) if obj.get("pass") is not None else None,
        "score": obj.get("score"),
        "reason": obj.get("reason", "")[:300],
        "raw": content[:200],
    }


def cell_records(eval_data: dict) -> list[dict]:
    """Pull regradable cells from an eval export.

    Skips cells where the llm-rubric assertion never ran (transport
    errors or `not-contains` failures). For each remaining cell, returns
    enough to reconstruct the grader call.
    """
    out = []
    rs = (eval_data.get("results") or {}).get("results") or []
    for r in rs:
        if r.get("failureReason") == 2:  # transport error — no output to grade
            continue
        prov = r["provider"].get("label") or r["provider"].get("id", "?")
        test = (r.get("testCase") or {}).get("description") or "?"
        user_prompt = (r.get("prompt") or {}).get("raw") or ""
        output = (r.get("response") or {}).get("output") or ""
        # Find the llm-rubric assertion (skip the not-contains stub-check).
        rubric = None
        for a in (r.get("testCase") or {}).get("assert") or []:
            if a.get("type") == "llm-rubric":
                rubric = a.get("value", "")
                break
        if not rubric:
            continue
        # Stored Sonnet verdict for the llm-rubric component specifically.
        sonnet_pass = None
        for c in (r.get("gradingResult") or {}).get("componentResults") or []:
            if (c.get("assertion") or {}).get("type") == "llm-rubric":
                sonnet_pass = bool(c.get("pass"))
                break
        if sonnet_pass is None:
            continue
        out.append({
            "provider": prov,
            "test": test,
            "user_prompt": user_prompt,
            "output": output,
            "rubric": rubric,
            "sonnet_pass": sonnet_pass,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eval", action="append", required=True,
                    help="promptfoo eval ID; pass multiple to merge (later evals overlay earlier).")
    ap.add_argument("--run-label", required=True,
                    help="namespace for cache entries (typically 'skill' or 'bare'). "
                    "Required so skill-loaded outputs and bare-control outputs for the "
                    "same (provider, test) don't collide in the cache.")
    ap.add_argument("--candidate", default="anthropic/claude-haiku-4.5",
                    help="candidate grader model on OpenRouter")
    ap.add_argument("--cache", default=".grader-agreement-cache.json",
                    help="JSON cache file (avoids paying twice on retry)")
    ap.add_argument("--limit", type=int, default=0,
                    help="only re-grade N cells (for smoke testing)")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("OPENROUTER_API_KEY not set")

    # Load + merge evals. Later evals overlay earlier ones per (provider, test):
    # promptfoo --filter-errors-only retries naturally produce this pattern.
    cells_by_key: dict[tuple[str, str], dict] = {}
    for eid in args.eval:
        print(f"loading {eid}...", file=sys.stderr)
        data = export_eval(eid)
        for c in cell_records(data):
            cells_by_key[(c["provider"], c["test"])] = c
    cells = list(cells_by_key.values())
    if args.limit:
        cells = cells[: args.limit]
    print(f"{len(cells)} cells to re-grade with {args.candidate}", file=sys.stderr)

    cache_path = Path(args.cache)
    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    agree_pp = agree_ff = disagree_pf = disagree_fp = unparsed = 0
    disagreements: list[dict] = []
    by_test_disagree: dict[str, int] = defaultdict(int)
    by_provider_disagree: dict[str, int] = defaultdict(int)

    for i, cell in enumerate(cells, 1):
        cache_key = f"{args.candidate}::{args.run_label}::{cell['provider']}::{cell['test']}"
        if cache_key in cache:
            verdict = cache[cache_key]
        else:
            prompt_text = RUBRIC_PROMPT_TEMPLATE.format(
                user_prompt=cell["user_prompt"],
                output=cell["output"],
                rubric=cell["rubric"],
            )
            verdict = call_grader(args.candidate, prompt_text, api_key)
            cache[cache_key] = verdict
            # Persist every 5 cells so a crash doesn't lose work.
            if i % 5 == 0:
                cache_path.write_text(json.dumps(cache, indent=2))

        if verdict["pass"] is None:
            unparsed += 1
            print(f"  [{i}/{len(cells)}] UNPARSED  {cell['provider'][:30]:30} | {cell['test'][:40]}", file=sys.stderr)
            continue

        s, h = cell["sonnet_pass"], verdict["pass"]
        if s and h: agree_pp += 1
        elif (not s) and (not h): agree_ff += 1
        elif s and not h:
            disagree_pf += 1
            disagreements.append({"provider": cell["provider"], "test": cell["test"], "sonnet": "PASS", "haiku": "FAIL", "haiku_reason": verdict["reason"]})
            by_test_disagree[cell["test"]] += 1
            by_provider_disagree[cell["provider"]] += 1
        else:
            disagree_fp += 1
            disagreements.append({"provider": cell["provider"], "test": cell["test"], "sonnet": "FAIL", "haiku": "PASS", "haiku_reason": verdict["reason"]})
            by_test_disagree[cell["test"]] += 1
            by_provider_disagree[cell["provider"]] += 1

        if i % 25 == 0:
            print(f"  [{i}/{len(cells)}] graded; agree {agree_pp+agree_ff} disagree {disagree_pf+disagree_fp} unparsed {unparsed}", file=sys.stderr)

    cache_path.write_text(json.dumps(cache, indent=2))

    total = agree_pp + agree_ff + disagree_pf + disagree_fp
    print()
    print("─" * 78)
    print(f"Agreement: {args.candidate} vs Sonnet 4.6")
    print("─" * 78)
    if total:
        print(f"  Agree PASS+PASS  {agree_pp:4} ({100*agree_pp/total:5.1f}%)")
        print(f"  Agree FAIL+FAIL  {agree_ff:4} ({100*agree_ff/total:5.1f}%)")
        print(f"  Disagree S=PASS Haiku=FAIL  {disagree_pf:4} ({100*disagree_pf/total:5.1f}%)  ← stricter")
        print(f"  Disagree S=FAIL Haiku=PASS  {disagree_fp:4} ({100*disagree_fp/total:5.1f}%)  ← looser")
        print(f"  Unparsed                    {unparsed:4}")
        print()
        print(f"  Overall agreement: {(agree_pp+agree_ff)/total*100:5.1f}%  (threshold for swap: ≥95%)")

    if disagreements:
        print()
        print("─" * 78)
        print(f"Disagreements by test (top 10)")
        print("─" * 78)
        for t, n in sorted(by_test_disagree.items(), key=lambda x: -x[1])[:10]:
            print(f"  {n:3}  {t[:65]}")
        print()
        print("─" * 78)
        print(f"Disagreements by provider")
        print("─" * 78)
        for p, n in sorted(by_provider_disagree.items(), key=lambda x: -x[1]):
            print(f"  {n:3}  {p}")
        print()
        print("─" * 78)
        print(f"Sample disagreement reasons (first 15)")
        print("─" * 78)
        for d in disagreements[:15]:
            print(f"  S={d['sonnet']:4} H={d['haiku']:4} | {d['provider'][:30]:30} | {d['test'][:35]:35} | {d['haiku_reason'][:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
