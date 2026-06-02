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
    parser.add_argument("--time-limit", type=float, default=3.0)
    parser.add_argument("--out", default="outputs/method_results.jsonl")
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    methods = [
        ("ca_discrepancy_monotonic", {"rule": "discrepancy", "relax": "monotonic", "initial": 0.0}),
        ("ca_topk_star_monotonic", {"rule": "topk_star", "relax": "monotonic", "initial": 1.0}),
        ("ca_gain_monotonic", {"rule": "gain", "relax": "monotonic", "initial": 0.0}),
    ]
    with Path(args.out).open("w", encoding="utf-8") as handle:
        for name in args.datasets:
            ds = load_named(args.data_dir, name, max_rows=args.max_rows, max_features=args.max_features)
            search = BinaryTreeSearch(ds.rows, ds.labels, ds.features, max_depth=args.depth, minsup=args.minsup)
            for method_name, cfg in methods:
                result = search.cadl85(time_limit=args.time_limit, **cfg)
                record = {
                    "dataset": name,
                    "method": method_name,
                    "depth": args.depth,
                    "minsup": args.minsup,
                    "n_rows": len(ds.labels),
                    "n_features": len(ds.features),
                    **result,
                }
                handle.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
