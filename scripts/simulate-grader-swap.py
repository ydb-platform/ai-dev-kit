#!/usr/bin/env python3
"""Project what the A/B matrix would look like with Haiku verdicts.

No new prompts to models-under-test — purely reclassifies cells by
substituting Haiku's pass/fail for Sonnet's on the llm-rubric. Uses
the .grader-agreement-cache.json populated by grader-agreement.py.

This is the dry-run answer to "if we swapped grader, what changes
in the baseline?" — useful as the decision input.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


def export_eval(eval_id: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    subprocess.run(
        ["npx", "--yes", "promptfoo@latest", "export", "eval", eval_id, "--output", path],
        check=True, capture_output=True,
    )
    with open(path) as fh:
        return json.load(fh)


def cell_map(data: dict, haiku_cache: dict, label: str) -> dict[tuple[str, str], dict]:
    """(provider, test) → {sonnet_pass, haiku_pass, transport_error}.

    sonnet_pass = the overall stored verdict (AND of all assertions).
    haiku_pass  = (not-contains was True) AND (haiku's llm-rubric verdict).
    """
    out: dict[tuple[str, str], dict] = {}
    rs = (data.get("results") or {}).get("results") or []
    for r in rs:
        prov = r["provider"].get("label") or r["provider"].get("id", "?")
        test = (r.get("testCase") or {}).get("description") or "?"
        transport_error = r.get("failureReason") == 2

        # The not-contains "[provider error]" assertion is component 0 in our config.
        not_contains_pass = True
        for c in (r.get("gradingResult") or {}).get("componentResults") or []:
            if (c.get("assertion") or {}).get("type") == "not-contains":
                not_contains_pass = bool(c.get("pass"))
                break

        cache_key = f"anthropic/claude-haiku-4.5::{label.split('-')[0]}::{prov}::{test}"
        haiku_verdict = haiku_cache.get(cache_key)
        haiku_pass = None
        if haiku_verdict and haiku_verdict.get("pass") is not None:
            haiku_pass = not_contains_pass and bool(haiku_verdict["pass"])

        out[(prov, test)] = {
            "sonnet_pass": bool(r.get("success")),
            "haiku_pass": haiku_pass,
            "transport_error": transport_error,
            "label": label,
        }
    return out


def overlay(base: dict, retry: dict) -> dict:
    merged = dict(base)
    for key, retry_cell in retry.items():
        base_cell = merged.get(key)
        if base_cell and base_cell["transport_error"]:
            merged[key] = retry_cell
    return merged


def classify(skill_pass: bool | None, bare_pass: bool | None) -> str:
    if skill_pass is None or bare_pass is None:
        return "UNRATED"
    if skill_pass and bare_pass:
        return "REDUNDANT"
    if skill_pass and not bare_pass:
        return "SKILL_WORKS"
    if not skill_pass and bare_pass:
        return "SKILL_HARMS"
    return "INSUFFICIENT"


def main() -> int:
    cache = json.loads(Path(".grader-agreement-cache.json").read_text())

    skill_base = cell_map(export_eval("eval-ptt-2026-05-25T10:51:38"), cache, "skill-base")
    skill_retry = cell_map(export_eval("eval-d2m-2026-05-25T11:12:55"), cache, "skill-retry")
    bare_base = cell_map(export_eval("eval-amm-2026-05-25T10:51:40"), cache, "bare-base")
    bare_retry = cell_map(export_eval("eval-V7j-2026-05-25T11:13:03"), cache, "bare-retry")

    skill = overlay(skill_base, skill_retry)
    bare = overlay(bare_base, bare_retry)

    print()
    print("─" * 78)
    print("Projected matrix under Haiku grader (no model re-prompting; pure reclassify)")
    print("─" * 78)
    print()

    counts_sonnet = defaultdict(int)
    counts_haiku = defaultdict(int)
    flips = []

    for key in sorted(set(skill) | set(bare)):
        s = skill.get(key)
        b = bare.get(key)
        if not s or not b:
            continue
        sonnet_verdict = classify(s["sonnet_pass"], b["sonnet_pass"])
        haiku_verdict = classify(s["haiku_pass"], b["haiku_pass"])
        counts_sonnet[sonnet_verdict] += 1
        counts_haiku[haiku_verdict] += 1
        if sonnet_verdict != haiku_verdict:
            flips.append((key[0], key[1], sonnet_verdict, haiku_verdict))

    cats = ["SKILL_WORKS", "REDUNDANT", "INSUFFICIENT", "SKILL_HARMS", "UNRATED"]
    total = sum(counts_sonnet.values())
    print(f"  {'verdict':14} {'Sonnet now':>12} {'Haiku proj':>12}  Δ")
    for c in cats:
        s = counts_sonnet.get(c, 0)
        h = counts_haiku.get(c, 0)
        d = h - s
        sign = "+" if d > 0 else ""
        print(f"  {c:14} {s:>5} ({100*s/total:5.1f}%) {h:>5} ({100*h/total:5.1f}%)  {sign}{d}")
    print()

    # Flip patterns
    flip_kinds = defaultdict(int)
    for _, _, s, h in flips:
        flip_kinds[f"{s} → {h}"] += 1
    print("─" * 78)
    print(f"Flips ({len(flips)} cells changed verdict)")
    print("─" * 78)
    for kind, n in sorted(flip_kinds.items(), key=lambda x: -x[1]):
        print(f"  {n:3}  {kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
