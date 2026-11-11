"""Command-line entry point: run one CA-DL8.5 instantiation as an oracle-protocol solver.

Example: python -m method.run_solver --rule discrepancy --relax monotonic
(reads the instance header on stdin; see briefing/evaluation.md).
"""

from __future__ import annotations

import argparse
import sys

from data.tree_oracle import Oracle
from method.cadl85 import CADL85


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule", required=True,
                        choices=["discrepancy", "topk", "topk_star", "gain", "purity"])
    parser.add_argument("--relax", default="monotonic", choices=["monotonic", "exponential", "luby"])
    parser.add_argument("--initial", type=float, default=None)
    parser.add_argument("--delta", type=float, default=None)
    args = parser.parse_args()
    sys.setrecursionlimit(10000)
    solver = CADL85(Oracle(), args.rule, args.relax, args.initial, args.delta)
    solver.run()
    print(f"iterations={solver.iterations} used={solver.o.used} incumbent={solver.incumbent} "
          f"proved={solver.proved}", file=sys.stderr)


if __name__ == "__main__":
    main()
