#!/bin/bash
# Rebuild the benchmark instances and their exact optima from the CP4IM data
# (run scripts/download.sh first). Deterministic: the committed instance files
# are reproduced exactly. CPU-heavy (~30 min); not needed for evaluation.
set -euo pipefail
cd /home/user
python -m eval.train.build_instances
if [ -f eval/test/build_instances.py ]; then
  python -m eval.test.build_instances
fi
