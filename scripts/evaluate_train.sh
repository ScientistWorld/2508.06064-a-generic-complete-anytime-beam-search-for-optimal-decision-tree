#!/bin/bash
# Train-slice evaluation: runs every registered solver (method/solvers.json,
# baseline/solvers.json) on the train instances through the oracle harness and
# writes scoring/scores_train.json. No arguments needed.
set -euo pipefail
cd /home/user
mkdir -p scoring
python -m eval.train.evaluate "$@"
