#!/bin/bash
# Run the paper's method (CA-DL8.5 instantiations registered in
# method/solvers.json) on the train instances and score them.
# The method needs no training: each solver is run per instance by the harness.
set -euo pipefail
cd /home/user
mkdir -p outputs
python -m eval.train.evaluate --registry method/solvers.json --out outputs/method_scores_train.json "$@"
