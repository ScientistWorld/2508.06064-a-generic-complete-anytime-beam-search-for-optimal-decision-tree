#!/bin/bash
# Held-out test-slice evaluation: runs every registered solver (method/solvers.json,
# baseline/solvers.json) on the hidden test instances through the oracle
# harness and writes scoring/scores_test.json. No arguments needed.
set -euo pipefail
cd /home/user
mkdir -p scoring
python -m eval.test.evaluate "$@"
