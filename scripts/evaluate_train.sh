#!/bin/bash
# Train-slice evaluation for the research gym.
#
# Mirrors scripts/evaluate.sh: it reads pre-generated JSONL result records,
# does not import method/, and writes a score file. The train slice scores the
# first half of each anytime trajectory.

set -euo pipefail

cd /home/user

mkdir -p scoring

python -m eval.train.evaluate "$@"
