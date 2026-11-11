#!/bin/bash
# Download all data needed for this environment. Idempotent: existing files
# are skipped, missing ones are fetched.
#
# The 24 CP4IM binary classification datasets used by the paper, in the dense
# 0/1 format distributed by the DL8.5 authors' pydl8.5 repository (pinned
# commit). The original CP4IM host (dtai-static.cs.kuleuven.be/CP4IM) no longer
# serves the files. Only the instance builders (eval/*/build_instances.py)
# read these files; solvers never see them.
#
# Estimated total download size: ~20 MB
# Estimated disk usage after extraction: ~20 MB

set -euo pipefail

cd "$(dirname "$0")/.."

SHA=a7f0fee72b4c17bbcb727050ba102db7dda10119
base="https://raw.githubusercontent.com/aia-uclouvain/pydl8.5/${SHA}/datasets"
mkdir -p data/downloads/cp4im
for d in anneal audiology australian-credit breast-wisconsin diabetes german-credit \
         heart-cleveland hepatitis hypothyroid ionosphere kr-vs-kp letter lymph mushroom \
         pendigits primary-tumor segment soybean splice-1 tic-tac-toe vehicle vote yeast zoo-1; do
  target="data/downloads/cp4im/${d}.txt"
  if [ ! -s "$target" ]; then
    curl -fsSL --retry 3 "${base}/${d}.txt" -o "${target}.part"
    mv "${target}.part" "$target"
  fi
done
