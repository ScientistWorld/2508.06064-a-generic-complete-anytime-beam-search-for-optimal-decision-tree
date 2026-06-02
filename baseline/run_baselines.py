from __future__ import annotations

import argparse
import json
from pathlib import Path

from data.cp4im import load_named
from method.dl85 import BinaryTreeSearch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/downloads")
    parser.add_argument("--datasets", nargs="+", default=["zoo-1", "vote", "tic-tac-toe"])
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--minsup", type=int, default=1)
    parser.add_argument("--max-rows", type=int, default=0, help="0 means all rows")
    parser.add_argument("--max-features", type=int, default=0, help="0 means all features")
    parser.add_argument("--include-exact", action="store_true", help="also run exact DL8.5 baseline")
    parser.add_argument("--out", default="outputs/baseline_results.jsonl")
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.out).open("w", encoding="utf-8") as handle:
        for name in args.datasets:
            ds = load_named(args.data_dir, name, max_rows=args.max_rows, max_features=args.max_features)
            search = BinaryTreeSearch(ds.rows, ds.labels, ds.features, max_depth=args.depth, minsup=args.minsup)
            baselines = [("c45_greedy", 1), ("top3", 3)]
            if args.include_exact:
                baselines.append(("dl85_exact", len(ds.features)))
            for method_name, top_k in baselines:
                if method_name == "dl85_exact":
                    result = search.exact_dl85()
                    events = [{"time": 0.0, "error": result.error, "optimal": True}]
                else:
                    result = search.greedy(top_k=top_k)
                    events = [{"time": 0.0, "error": result.error, "optimal": False}]
                handle.write(json.dumps({
                    "dataset": name,
                    "method": method_name,
                    "depth": args.depth,
                    "minsup": args.minsup,
                    "n_rows": len(ds.labels),
                    "n_features": len(ds.features),
                    "incumbent_error": result.error,
                    "proved_optimal": method_name == "dl85_exact",
                    "events": events,
                }) + "\n")


if __name__ == "__main__":
    main()
