from __future__ import annotations

import argparse
import json
from pathlib import Path


def primal_integral(events: list[dict], optimal_error: int, horizon: float) -> float:
    events = sorted(events, key=lambda e: e.get("time", 0.0))
    if not events:
        return horizon
    total = 0.0
    current_error = events[0]["error"]
    current_time = 0.0
    for event in events[1:]:
        t = min(float(event["time"]), horizon)
        if t > current_time:
            total += gap(current_error, optimal_error) * (t - current_time)
        current_error = min(current_error, int(event["error"]))
        current_time = t
        if current_time >= horizon:
            break
    if current_time < horizon:
        total += gap(current_error, optimal_error) * (horizon - current_time)
    return total / horizon


def gap(error: int, optimal_error: int) -> float:
    if error <= 0:
        return 0.0
    return abs(error - optimal_error) / abs(error)


def summarize(records: list[dict], horizon: float) -> dict:
    grouped: dict[str, list[dict]] = {}
    for rec in records:
        grouped.setdefault(rec["method"], []).append(rec)
    results = {}
    for method, rows in grouped.items():
        pis = [primal_integral(r["events"], int(r["optimal_error"]), horizon) for r in rows]
        rel_errors = [
            (r["incumbent_error"] - r["optimal_error"]) / max(1, r["n_rows"])
            for r in rows
        ]
        solved = [1.0 if r.get("proved_optimal") else 0.0 for r in rows]
        results[method] = {
            "avg_primal_gap_integral": sum(pis) / len(pis),
            "avg_excess_error_rate": sum(rel_errors) / len(rel_errors),
            "optimality_proved_rate": sum(solved) / len(solved),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", default=["outputs/baseline_results.jsonl", "outputs/method_results.jsonl"])
    parser.add_argument("--horizon", type=float, default=3.0)
    parser.add_argument("--out", default="scoring/scores.json")
    args = parser.parse_args()

    records = []
    for path in args.inputs:
        p = Path(path)
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    if not records:
        raise SystemExit("no result records found")
    scores = {
        "experiments": {
            "depth4_cp4im_anytime": {
                "results": summarize(records, args.horizon)
            }
        }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
