#!/usr/bin/env python3
"""Compare a main (skill-loaded) promptfoo eval against a bare control.

For each (provider, test) cell, joins the verdicts from the two runs into
one of four buckets:

  skill PASS + bare PASS  →  REDUNDANT     — claim already in training memory
  skill PASS + bare FAIL  →  SKILL WORKS   — load-bearing content
  skill FAIL + bare PASS  →  SKILL HARMS   — rare; investigate
  skill FAIL + bare FAIL  →  INSUFFICIENT  — text exists but isn't enough

Usage:
  # Auto-pick the latest eval of each config (matched by description field):
  python3 scripts/ab-compare.py

  # Pin specific eval IDs:
  python3 scripts/ab-compare.py --skill eval-XYZ --bare eval-ABC

Requires: `npx promptfoo@latest export eval ...` on $PATH.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

SKILL_DESCRIPTION = "YDB skills compatibility matrix"
BARE_DESCRIPTION = "YDB skills A/B control (bare — no skill content loaded)"


def run(cmd: list[str], capture: bool = True) -> str:
    res = subprocess.run(cmd, capture_output=capture, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr or "")
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return res.stdout


def list_evals() -> list[dict]:
    """Return promptfoo's eval list as a parsed structure.

    `promptfoo list evals` prints a table; easier path is reading the
    sqlite at ~/.promptfoo/promptfoo.db, but that adds a dep. Fall back
    to parsing --ids-only and inspecting each via export.
    """
    out = run(["npx", "--yes", "promptfoo@latest", "list", "evals", "-n", "20", "--ids-only"])
    ids = [line.strip() for line in out.splitlines() if line.strip().startswith("eval-")]
    return [{"id": eid} for eid in ids]


def export_eval(eval_id: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    run(["npx", "--yes", "promptfoo@latest", "export", "eval", eval_id, "--output", path])
    with open(path) as fh:
        return json.load(fh)


def find_latest(target_description: str) -> str:
    """Walk recent evals; return the first whose config.description matches."""
    for entry in list_evals():
        data = export_eval(entry["id"])
        desc = (data.get("config") or {}).get("description") or ""
        if desc == target_description:
            return entry["id"]
    raise SystemExit(f"no recent eval found with description {target_description!r}")


def cell_map(data: dict) -> dict[tuple[str, str], dict]:
    """Map (provider_label, test_description) → {success, error, output}."""
    out: dict[tuple[str, str], dict] = {}
    rs = (data.get("results") or {}).get("results") or []
    for r in rs:
        prov = r["provider"].get("label") or r["provider"].get("id", "?")
        test = (r.get("testCase") or {}).get("description") or "?"
        out[(prov, test)] = {
            "success": bool(r.get("success")),
            "error": r.get("error"),
            "output": ((r.get("response") or {}).get("output") or "")[:200],
        }
    return out


def classify(skill_pass: bool, bare_pass: bool, skill_err: bool, bare_err: bool) -> str:
    if skill_err or bare_err:
        return "ERROR"
    if skill_pass and bare_pass:
        return "REDUNDANT"
    if skill_pass and not bare_pass:
        return "SKILL_WORKS"
    if not skill_pass and bare_pass:
        return "SKILL_HARMS"
    return "INSUFFICIENT"


VERDICT_GLYPH = {
    "REDUNDANT": ".",       # both pass — meh
    "SKILL_WORKS": "+",     # skill earns its keep
    "SKILL_HARMS": "!",     # skill hurts — investigate
    "INSUFFICIENT": "x",    # neither passes — text isn't enough
    "ERROR": "?",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", help="eval ID of the main (skill-loaded) run")
    parser.add_argument("--bare", help="eval ID of the bare control run")
    args = parser.parse_args()

    skill_id = args.skill or find_latest(SKILL_DESCRIPTION)
    bare_id = args.bare or find_latest(BARE_DESCRIPTION)
    print(f"skill eval: {skill_id}")
    print(f"bare eval:  {bare_id}\n")

    skill_data = export_eval(skill_id)
    bare_data = export_eval(bare_id)
    skill_cells = cell_map(skill_data)
    bare_cells = cell_map(bare_data)

    # Per-test summary across providers.
    per_test: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_cell: list[tuple[str, str, str]] = []
    counts: dict[str, int] = defaultdict(int)

    keys = sorted(set(skill_cells) | set(bare_cells))
    for prov, test in keys:
        s = skill_cells.get((prov, test))
        b = bare_cells.get((prov, test))
        if not s or not b:
            continue
        verdict = classify(
            s["success"], b["success"], bool(s["error"]), bool(b["error"])
        )
        per_test[test][verdict] += 1
        per_cell.append((prov, test, verdict))
        counts[verdict] += 1

    total = sum(counts.values())
    print("─" * 78)
    print("Headline (cells across all providers × tests)")
    print("─" * 78)
    for v in ("SKILL_WORKS", "REDUNDANT", "INSUFFICIENT", "SKILL_HARMS", "ERROR"):
        c = counts.get(v, 0)
        pct = (100 * c / total) if total else 0
        print(f"  {VERDICT_GLYPH[v]} {v:14}  {c:3}  ({pct:5.1f}%)")
    print()

    print("─" * 78)
    print("Per-test (aggregated across providers)")
    print("─" * 78)
    header = f"  {'TEST':55} {'works':>5} {'redu':>5} {'insuf':>5} {'harms':>5}"
    print(header)
    for test in sorted(per_test):
        c = per_test[test]
        print(
            f"  {test[:55]:55} "
            f"{c.get('SKILL_WORKS',0):5} "
            f"{c.get('REDUNDANT',0):5} "
            f"{c.get('INSUFFICIENT',0):5} "
            f"{c.get('SKILL_HARMS',0):5}"
        )
    print()

    print("─" * 78)
    print("Per-cell (sorted by verdict)")
    print("─" * 78)
    order = {"SKILL_HARMS": 0, "INSUFFICIENT": 1, "SKILL_WORKS": 2, "ERROR": 3, "REDUNDANT": 4}
    per_cell.sort(key=lambda x: (order.get(x[2], 9), x[1], x[0]))
    for prov, test, verdict in per_cell:
        print(f"  {VERDICT_GLYPH[verdict]} {verdict:13}  {prov:40}  {test[:45]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
