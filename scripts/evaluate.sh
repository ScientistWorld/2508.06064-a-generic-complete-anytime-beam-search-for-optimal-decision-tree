#!/bin/bash
# Standard evaluation entry point. Solvers are programs that speak the oracle
# protocol (briefing/evaluation.md) and are registered in method/solvers.json
# (or baseline/solvers.json). This scores every registered solver on the train
# instances and writes scoring/scores.json; it never imports method/.
#
# Usage: bash scripts/evaluate.sh [--solvers NAME ...]
set -euo pipefail
cd /home/user
mkdir -p scoring
python -m eval.train.evaluate --out scoring/scores.json "$@"
