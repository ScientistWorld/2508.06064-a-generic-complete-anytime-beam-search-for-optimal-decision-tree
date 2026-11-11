#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python -m redteam.audit restore' EXIT
for case in reference_seed0 reference_seed1 reference_seed2 \
    better_more_search weaker_no_restarts bruteforce_shortcut \
    copy_answers_shortcut retime_shortcut comparison_replacement_shortcut \
    omit_hard_shortcut duplicate_easy_shortcut no_proof_shortcut \
    filter_methods_shortcut direct_scores_shortcut negative_error_shortcut \
    empty_output_shortcut null_error_shortcut stale_failure_shortcut; do
    bash "redteam/$case/run.sh"
done
python -m redteam.audit summarize
