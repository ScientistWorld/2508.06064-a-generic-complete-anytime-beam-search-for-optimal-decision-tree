#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -euo pipefail

cd /home/user

python -m method.run_cadl85 --datasets vote tic-tac-toe --depth 4 --max-features 16 --max-rows 0 --time-limit 3.0 "$@"
bash scripts/evaluate.sh --horizon 3.0
