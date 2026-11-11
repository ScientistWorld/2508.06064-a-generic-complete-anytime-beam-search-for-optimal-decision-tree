#!/bin/bash
# Reproduce the gym's reference results end to end (CPU only).
#   1. build the instances if they are missing (exact optima, ~30 min);
#   2. run the baselines and every CA-DL8.5 instantiation on the train slice
#      (scoring/scores_train.json and scoring/scores.json);
#   3. run them on the held-out test slice when it is present
#      (scoring/scores_test.json).
set -euo pipefail
cd /home/user
[ -s eval/train/instances.json ] || python -m eval.train.build_instances
if [ -f eval/test/build_instances.py ]; then
  [ -s eval/test/instances.json ] || python -m eval.test.build_instances
fi
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
if [ -f eval/test/evaluate.py ]; then
  bash scripts/evaluate_test.sh
fi
