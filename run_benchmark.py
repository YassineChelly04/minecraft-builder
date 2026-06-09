"""
run_benchmark.py — the scoreboard. Two dashboards: quality up, tokens down.

    python run_benchmark.py --suite buildings --no-llm
    python run_benchmark.py --suite buildings --quick
    python run_benchmark.py --suite all --agent interior --model llama-3.3-70b-versatile

Loads fixed prompts, runs the pipeline with refine off, scores each build with
quality.score_build, prints a table (prompt | total | failing | tokens | Δ vs
last run) and appends every row to benchmarks/runs.jsonl.

--no-llm runs the whole deterministic path against StubLLM (zero network), so the
~90% of the system that is Python is testable offline and in CI.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent
BENCH = ROOT / "benchmarks"
RUNS = BENCH / "runs.jsonl"


def _load_prompts(suite: str) -> list[dict]:
    f = BENCH / f"prompts_{suite}.json"
    return json.loads(f.read_text(encoding="utf-8"))


def _last_run() -> dict[str, dict]:
    """Most recent score per prompt id from runs.jsonl (for the Δ column)."""
    if not RUNS.exists():
        return {}
    last: dict[str, dict] = {}
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        last[row.get("id", "")] = row
    return last


def _append_runs(rows: list[dict]) -> None:
    BENCH.mkdir(exist_ok=True)
    with RUNS.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _run_building(entry: dict, stub: bool) -> dict:
    from llm_client import stub_mode
    from pipeline import build_structure
    from quality import score_build

    t0 = time.time()
    with stub_mode(stub):
        result = build_structure(
            prompt=entry["prompt"], origin=entry.get("origin", {"x": 0, "y": 64, "z": 0}),
            answers=entry.get("answers") or {}, brief=None, refine=False,
        )
    geometry = result.get("geometry")
    score = score_build(result["commands"], result.get("intent", {}), geometry)
    return {
        "id": entry["id"],
        "prompt": entry["prompt"],
        "total": round(score.total, 1),
        "failing": score.failing,
        "tokens": result.get("usage", {}).get("total_tokens", 0),
        "commands": len(result["commands"]),
        "valid": result.get("valid"),
        "secs": round(time.time() - t0, 2),
    }


def _print_table(rows: list[dict], prev: dict[str, dict]) -> None:
    print(f"\n{'id':<18}{'score':>7}{'delta':>7}{'tokens':>9}{'cmds':>7}  {'valid':<6} failing")
    print("-" * 92)
    tot_score = tot_tok = 0.0
    for r in rows:
        old = prev.get(r["id"], {})
        delta = (r["total"] - old["total"]) if "total" in old else None
        ds = f"{delta:+.1f}" if delta is not None else "-"
        fail = ",".join(r["failing"][:4]) or "-"
        print(f"{r['id']:<18}{r['total']:>7.1f}{ds:>7}{r['tokens']:>9}{r['commands']:>7}  "
              f"{str(r['valid']):<6} {fail}")
        tot_score += r["total"]
        tot_tok += r["tokens"]
    n = len(rows) or 1
    print("-" * 92)
    print(f"{'MEAN':<18}{tot_score / n:>7.1f}{'':>7}{int(tot_tok / n):>9}")
    print(f"{'TOTAL TOKENS':<18}{'':>7}{'':>7}{int(tot_tok):>9}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["buildings", "cities", "all"], default="buildings")
    ap.add_argument("--quick", action="store_true", help="first 3 prompts only")
    ap.add_argument("--no-llm", action="store_true", help="run offline against StubLLM")
    ap.add_argument("--agent", help="A/B: role to override the model for")
    ap.add_argument("--model", help="A/B: model id for --agent")
    ap.add_argument("--prompt-variant", help="A/B: prompt variant tag (reserved)")
    args = ap.parse_args()

    # A/B model override via the same env lever config.py reads.
    if args.agent and args.model:
        os.environ[f"LLM_MODEL_{args.agent.upper()}"] = args.model

    suites = ["buildings", "cities"] if args.suite == "all" else [args.suite]
    prev = _last_run()
    all_rows: list[dict] = []

    for suite in suites:
        prompts = _load_prompts(suite)
        if args.quick:
            prompts = prompts[:3]
        print(f"\n=== suite: {suite} ({len(prompts)} prompts, "
              f"{'stub' if args.no_llm else 'live'} LLM) ===")
        rows = []
        for entry in prompts:
            try:
                if suite == "buildings":
                    row = _run_building(entry, stub=args.no_llm)
                else:
                    row = _run_city(entry, stub=args.no_llm)
            except Exception as e:  # noqa: BLE001 — one bad prompt shouldn't kill the suite
                row = {"id": entry["id"], "prompt": entry["prompt"], "total": 0.0,
                       "failing": [f"ERROR: {e}"], "tokens": 0, "commands": 0,
                       "valid": False, "secs": 0.0}
            row["suite"] = suite
            row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            rows.append(row)
        _print_table(rows, prev)
        all_rows.extend(rows)

    _append_runs(all_rows)


def _run_city(entry: dict, stub: bool) -> dict:
    """Wired in Phase F. Until then, report as pending so --suite all doesn't crash."""
    try:
        from city_pipeline import build_city  # noqa: F401
    except Exception:
        return {"id": entry["id"], "prompt": entry["prompt"], "total": 0.0,
                "failing": ["city-engine-not-built-yet"], "tokens": 0,
                "commands": 0, "valid": None, "secs": 0.0}
    from llm_client import stub_mode
    from city_pipeline import build_city
    from quality import score_city
    t0 = time.time()
    with stub_mode(stub):
        result = build_city(entry["prompt"], entry.get("origin", {"x": 0, "y": 64, "z": 0}),
                            entry.get("answers") or {}, mode="datapack")
    score = score_city(result["plan"], result["commands"])
    return {"id": entry["id"], "prompt": entry["prompt"], "total": round(score.total, 1),
            "failing": score.failing, "tokens": result.get("usage", {}).get("total_tokens", 0),
            "commands": len(result["commands"]), "valid": True, "secs": round(time.time() - t0, 2)}


if __name__ == "__main__":
    main()
