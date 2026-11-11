"""Score every registered solver on the held-out TEST slice of the anytime optimal-tree benchmark.

Solvers are discovered from the registries (default: ``method/solvers.json``
and ``baseline/solvers.json``; see briefing/evaluation.md for the format).
Each solver runs once per instance as a subprocess speaking the oracle
protocol of ``harness.py``; nothing the solver writes is trusted except the
trees, which the harness validates and scores against the data itself.

Scored per experiment: the average primal gap integral over the effort budget
and the average primal gap of the final incumbent (both lower is better).

A solver's run is failed -- worst value in every metric of every experiment --
if it fails on any instance (protocol violation, invalid tree, crash, timeout)
or if it does not prove optimality on every completeness-check instance, whose
budgets far exceed the size of their whole search space (the completeness
constraint: a complete method must be able to certify the optimum).

Usage: python -m eval.test.evaluate        (no arguments needed)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from eval.test.harness import Instance, RunRecord, final_gap, primal_integral, run_solver

SLICE = "test"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DEFAULT_REGISTRIES = ["method/solvers.json", "baseline/solvers.json"]
EXPERIMENTS = ["anytime_depth4", "anytime_depth5"]
METRICS = ["avg_primal_gap_integral", "avg_final_primal_gap"]
WORST = {"avg_primal_gap_integral": 1.0, "avg_final_primal_gap": 1.0}
GATE = "completeness"


def load_registries(paths: list[str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return (solvers, problems); a malformed entry is kept as a failed solver."""
    solvers: dict[str, list[str]] = {}
    problems: dict[str, str] = {}
    for rel in paths:
        path = Path(rel) if os.path.isabs(rel) else ROOT / rel
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            entries = data.get("solvers", data)
            items = list(entries.items())
        except Exception as exc:
            print(f"[{SLICE}] unreadable registry {path}: {exc!r}", file=sys.stderr)
            continue
        for name, entry in items:
            if not isinstance(name, str) or name.startswith("_"):
                continue
            command = entry.get("command") if isinstance(entry, dict) else entry
            if name in solvers or name in problems:
                problems[name] = "registered more than once"
                solvers.pop(name, None)
            elif not (isinstance(command, list) and command and all(isinstance(a, str) for a in command)):
                problems[name] = "registry entry needs a non-empty command list"
            else:
                solvers[name] = command
    return solvers, problems


def load_instances() -> list[tuple[dict, int]]:
    specs = json.loads((HERE / "instances.json").read_text())["instances"]
    answers = json.loads((HERE / "answers.json").read_text())
    return [(spec, int(answers[spec["name"]]["optimal_error"])) for spec in specs]


def _task(args):
    name, command, spec, optimal, wall, stderr_path = args
    try:
        inst = Instance.from_json(spec, optimal)
        rec = run_solver(command, inst, ROOT, wall, Path(stderr_path) if stderr_path else None).to_json()
    except Exception as exc:  # an evaluator-side error fails the run, never scores it
        rec = {"instance": spec["name"], "experiment": spec["experiment"], "budget": spec["budget"],
               "optimal_error": optimal, "failed": True, "events": [], "final_error": None,
               "used": 0, "proved": False,
               "failure": f"evaluator error: {exc!r}: {traceback.format_exc(limit=3)}"}
    return name, rec


def write_scores(path: Path, results: dict, extra: dict) -> None:
    payload = {"experiments": {}}
    for exp in EXPERIMENTS:
        payload["experiments"][exp] = {"slice": SLICE, **extra.get(exp, {}), "results": results.get(exp, {})}
    for key, value in extra.items():
        if key not in EXPERIMENTS:
            payload[key] = value
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, path)


def worst(names) -> dict:
    return {exp: {name: dict(WORST) for name in names} for exp in EXPERIMENTS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "scoring" / "scores_test.json"))
    parser.add_argument("--registry", action="append", default=None,
                        help="solver registry JSON (repeatable); default: method/ and baseline/ registries")
    parser.add_argument("--solvers", nargs="*", default=None, help="restrict to these registered names")
    parser.add_argument("--jobs", type=int, default=0, help="parallel runs (default: available CPUs)")
    parser.add_argument("--wall-limit", type=float, default=1200.0, help="seconds per run (safety cap)")
    parser.add_argument("--runs-dir", default=None, help="optional directory for per-run records and logs")
    parser.add_argument("--verbose", action="store_true", help="print one line per run to stdout")
    args = parser.parse_args()
    log = sys.stdout if args.verbose else open(os.devnull, "w")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Never leave an older score file behind: start from an empty one.
    write_scores(out, {}, {"status": "evaluation started"})

    solvers, problems = load_registries(args.registry or DEFAULT_REGISTRIES)
    if args.solvers is not None:
        keep = set(args.solvers)
        solvers = {n: c for n, c in solvers.items() if n in keep}
        problems = {n: p for n, p in problems.items() if n in keep}
    names = sorted(set(solvers) | set(problems))
    # Until every run has finished, every solver holds worst values only.
    write_scores(out, worst(names), {"status": "incomplete evaluation"})
    instances = load_instances()

    runs_dir = Path(args.runs_dir) if args.runs_dir else None
    tasks = []
    for name, command in solvers.items():
        for spec, optimal in instances:
            stderr_path = None
            if runs_dir:
                d = runs_dir / name
                d.mkdir(parents=True, exist_ok=True)
                stderr_path = str(d / (spec["name"].replace("/", "__") + ".stderr"))
            tasks.append((name, command, spec, optimal, args.wall_limit, stderr_path))
    jobs = args.jobs or max(1, len(os.sched_getaffinity(0)))
    records: dict[str, list[dict]] = {name: [] for name in solvers}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for name, rec in pool.map(_task, tasks):
            records[name].append(rec)
            tag = "FAILED " + rec.get("failure", "") if rec["failed"] else (
                f"final={rec['final_error']} opt={rec['optimal_error']} used={rec['used']} proved={rec['proved']}")
            print(f"[{SLICE}] {name} {rec['instance']}: {tag}", flush=True, file=log)

    results = {exp: {} for exp in EXPERIMENTS}
    status, gate_info, proved_info = {}, {}, {exp: {} for exp in EXPERIMENTS}
    ungated = {exp: {} for exp in EXPERIMENTS}  # unranked: metrics of solvers failing only the gate
    for name in names:
        if name in problems:
            status[name] = "failed: " + problems[name]
            for exp in EXPERIMENTS:
                results[exp][name] = dict(WORST)
            continue
        recs = records[name]
        # (status messages never name instances: the instance list stays private)
        failures = sorted({r.get("failure", "").split(":")[0][:200] for r in recs if r["failed"]})
        n_failed = sum(1 for r in recs if r["failed"])
        gate = [r for r in recs if r["experiment"] == GATE]
        unproved = [r for r in gate if not r["proved"]]
        gate_info[name] = {"instances": len(gate), "proved": len(gate) - len(unproved)}
        if failures:
            status[name] = f"failed: {n_failed} of {len(recs)} runs failed ({'; '.join(failures)})"
        elif not gate or unproved:
            status[name] = (f"failed: optimality not proved on {len(unproved)} of {len(gate)} "
                            "completeness-check instances")
        else:
            status[name] = "ok"
        for exp in EXPERIMENTS:
            rows = [RunRecord(**{k: r[k] for k in RunRecord.__dataclass_fields__ if k in r})
                    for r in recs if r["experiment"] == exp]
            proved_info[exp][name] = sum(1 for r in rows if r.proved)
            values = {
                "avg_primal_gap_integral": sum(primal_integral(r) for r in rows) / len(rows),
                "avg_final_primal_gap": sum(final_gap(r) for r in rows) / len(rows),
            } if rows else dict(WORST)
            if status[name] == "ok" and rows:
                results[exp][name] = values
            else:
                results[exp][name] = dict(WORST)
                if not failures and rows:
                    ungated[exp][name] = values
        if runs_dir:
            (runs_dir / name / "records.json").write_text(json.dumps(recs, indent=1) + "\n")
    extra = {}
    for exp in EXPERIMENTS:
        rows = [spec for spec, _ in instances if spec["experiment"] == exp]
        extra[exp] = {"instances": len(rows),
                      "budgets": sorted({spec["budget"] for spec in rows}),
                      "max_depth": sorted({spec["max_depth"] for spec in rows}),
                      "n_features": sorted({spec["n_features"] for spec in rows}),
                      "proved_instances": proved_info[exp],
                      "unranked_metrics_of_solvers_failing_only_completeness": ungated[exp]}
    extra["status"] = status
    extra["completeness_check"] = gate_info
    write_scores(out, results, extra)
    bad = [n for n, s in status.items() if s != "ok"]
    if bad:
        print(f"[{SLICE}] solvers scored as failed: {bad}", file=sys.stderr)


if __name__ == "__main__":
    main()
