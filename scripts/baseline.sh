#!/bin/bash
# Run the baselines (C4.5-style greedy, Top-3/Top-5 DL8.5, DL8.5) registered in
# baseline/solvers.json on the train instances and score them.
set -euo pipefail
cd /home/user
mkdir -p outputs
python -m eval.train.evaluate --registry baseline/solvers.json --out outputs/baseline_scores_train.json "$@"
