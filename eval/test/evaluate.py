from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPERIMENT = "depth4_cp4im_anytime"
SLICE = "test"


def gap(error: int, optimal_error: int) -> float:
    if error <= 0:
        return 0.0
    return abs(error - optimal_error) / abs(error)


def instance_key(record: dict) -> tuple:
    return (
        record["dataset"],
        record.get("depth"),
        record.get("minsup"),
        record.get("n_rows"),
        record.get("n_features"),
    )


def read_records(paths: list[str]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    if not records:
        raise SystemExit("no result records found")
    return records


def result_inputs(result_roots: list[str], explicit_inputs: list[str] | None) -> list[str]:
    if explicit_inputs:
        return explicit_inputs

    root_candidates: list[Path] = []
    for root in result_roots:
        base = Path(root)
        if base.is_file():
            root_candidates.append(base)
            continue
        root_candidates.extend(
            [
                base / "baseline_results.jsonl",
                base / "method_results.jsonl",
                base / "outputs" / "baseline_results.jsonl",
                base / "outputs" / "method_results.jsonl",
            ]
        )

    candidates = [candidate for candidate in root_candidates if candidate.exists()]
    if not candidates:
        candidates = [
            Path("outputs/baseline_results.jsonl"),
            Path("outputs/method_results.jsonl"),
        ]

    seen: set[Path] = set()
    inputs: list[str] = []
    for candidate in candidates:
        normalized = candidate.resolve() if candidate.exists() else candidate
        if normalized not in seen:
            seen.add(normalized)
            inputs.append(str(candidate))
    return inputs


def train_methods(path: str) -> list[str] | None:
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    experiments = data.get("experiments", data)
    experiment = experiments.get(EXPERIMENT)
    if not isinstance(experiment, dict):
        raise ValueError(f"{path} does not contain experiment {EXPERIMENT!r}")
    results = experiment.get("results", experiment)
    if not isinstance(results, dict) or not results:
        raise ValueError(f"{path} does not contain method results for {EXPERIMENT!r}")
    return sorted(name for name in results if not name.startswith("_"))


def exact_optima(records: list[dict]) -> dict[tuple, int]:
    optima: dict[tuple, int] = {}
    for record in records:
        if record.get("method") == "dl85_exact" and record.get("proved_optimal"):
            optima[instance_key(record)] = int(record["incumbent_error"])
    return optima


def sorted_events(record: dict) -> list[dict]:
    events = sorted(record.get("events", []), key=lambda event: float(event.get("time", 0.0)))
    if not events:
        raise ValueError(f"missing anytime events for {record.get('method')} on {record.get('dataset')}")
    return events


def incumbent_error_at(record: dict, when: float) -> int:
    events = sorted_events(record)
    current_error = int(events[0]["error"])
    for event in events:
        if float(event.get("time", 0.0)) > when:
            break
        current_error = min(current_error, int(event["error"]))
    return current_error


def proof_time(record: dict, optimal_error: int, horizon: float) -> float | None:
    events = sorted_events(record)
    for event in events:
        if event.get("optimal") and int(event["error"]) == optimal_error:
            return float(event.get("time", 0.0))
    if record.get("proved_optimal") and int(record.get("incumbent_error", -1)) == optimal_error:
        # The proof-rate constraint must be backed by the anytime trace. Some
        # legacy records only have a terminal proved_optimal flag; count those
        # as certified at the horizon, not as an immediate proof.
        return horizon
    return None


def window_primal_integral(record: dict, optimal_error: int, start: float, end: float) -> float:
    if end <= start:
        raise ValueError(f"invalid scoring window: start={start}, end={end}")

    events = sorted_events(record)
    current_error = incumbent_error_at(record, start)
    current_time = start
    total = 0.0

    for event in events:
        event_time = min(float(event.get("time", 0.0)), end)
        if event_time <= start:
            continue
        if event_time > current_time:
            total += gap(current_error, optimal_error) * (event_time - current_time)
        current_error = min(current_error, int(event["error"]))
        current_time = event_time
        if current_time >= end:
            break

    if current_time < end:
        total += gap(current_error, optimal_error) * (end - current_time)
    return total / (end - start)


def summarize(
    records: list[dict],
    horizon: float,
    start: float,
    end: float,
    requested_methods: list[str] | None,
) -> dict[str, dict[str, float]]:
    optima = exact_optima(records)
    requested = set(requested_methods) if requested_methods is not None else None
    grouped: dict[str, list[dict]] = {}

    for record in records:
        key = instance_key(record)
        if key not in optima:
            raise ValueError(
                "missing dl85_exact proved optimum for "
                f"dataset={key[0]!r}, depth={key[1]}, minsup={key[2]}, "
                f"n_rows={key[3]}, n_features={key[4]}"
            )
        method = record["method"]
        if requested is None or method in requested:
            grouped.setdefault(method, []).append(record)

    if requested is not None:
        missing = sorted(requested.difference(grouped))
        if missing:
            raise ValueError(
                "test outputs are missing methods present in scoring/scores_train.json: "
                + ", ".join(missing)
            )

    results: dict[str, dict[str, float]] = {}
    for method, rows in sorted(grouped.items()):
        integrals = []
        excess_error_rates = []
        proof_states = []
        for row in rows:
            optimal_error = optima[instance_key(row)]
            terminal_error = incumbent_error_at(row, end)
            if terminal_error < optimal_error:
                raise ValueError(
                    f"{method} on {row['dataset']} has incumbent error {terminal_error} "
                    f"below proved optimum {optimal_error}"
                )
            integrals.append(window_primal_integral(row, optimal_error, start, end))
            excess_error_rates.append((terminal_error - optimal_error) / max(1, int(row["n_rows"])))
            reached_proof = proof_time(row, optimal_error, horizon)
            proof_states.append(1.0 if reached_proof is not None and reached_proof <= end else 0.0)

        results[method] = {
            "avg_primal_gap_integral": sum(integrals) / len(integrals),
            "avg_excess_error_rate": sum(excess_error_rates) / len(excess_error_rates),
            "optimality_proved_rate": sum(proof_states) / len(proof_states),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_roots", nargs="*", help="optional result directories or JSONL files to score")
    parser.add_argument("--inputs", nargs="+", default=None)
    parser.add_argument("--horizon", type=float, default=3.0)
    parser.add_argument("--out", default="scoring/scores_test.json")
    parser.add_argument("--train-scores", default="scoring/scores_train.json")
    args = parser.parse_args()

    start = args.horizon / 2.0
    end = args.horizon
    methods = train_methods(args.train_scores)
    inputs = result_inputs(args.result_roots, args.inputs)
    scores = {
        "experiments": {
            EXPERIMENT: {
                "slice": SLICE,
                "window": {"start": start, "end": end, "horizon": args.horizon},
                "methods_source": args.train_scores if methods is not None else "inputs",
                "results": summarize(read_records(inputs), args.horizon, start, end, methods),
            }
        }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
