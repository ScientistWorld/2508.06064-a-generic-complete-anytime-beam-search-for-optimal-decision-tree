#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -euo pipefail

cd /home/user

python -m method.run_cadl85 "$@"
bash scripts/evaluate.sh
