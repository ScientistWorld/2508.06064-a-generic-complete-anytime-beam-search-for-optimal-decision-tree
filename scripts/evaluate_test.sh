#!/bin/bash
# Held-out test-slice evaluation for the research gym.
#
# Mirrors scripts/evaluate.sh: it reads pre-generated JSONL result records,
# does not import method/, and writes a score file. The test slice scores the
# second half of each anytime trajectory and, when scoring/scores_train.json is
# present, evaluates the same method entries recorded by the train slice.

set -euo pipefail

cd /home/user

mkdir -p scoring

python -m eval.test.evaluate "$@"
