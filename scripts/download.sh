#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: <1 MB
# Estimated disk usage after extraction: <1 MB
#
# This script writes only to workspace-local paths so a fresh clone can
# reconstruct the required inputs without relying on machine-specific caches.

set -euo pipefail

cd /home/user

mkdir -p data/downloads
base="https://dtai-static.cs.kuleuven.be/CP4IM/datasets/data"
for dataset in zoo-1 vote tic-tac-toe; do
  target="data/downloads/${dataset}.txt"
  [ -e "$target" ] || curl -fL "$base/${dataset}.txt" -o "$target"
done
