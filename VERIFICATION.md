# Verification Report

## Initial Assessment

The workspace started at `core_claim` with a working CA-DL8.5 reproduction,
generated CP4IM output traces, method-agnostic evaluation code, train/test score
artifacts, and a passing `python validate.py --compare`. The claimed milestone
was justified: the implementation follows the paper's branch-and-bound
decision-tree search with complete-anytime restart/relaxation rules, and the
scaled benchmark shows proposed variants improving over static greedy baselines.

## Issues Found

- **Critical:** The primary scored primal-integral metric originally used
  recorded wall-clock event timestamps. That made the gym score partly
  hardware-dependent.
- **Minor:** The scaled `depth4_cp4im_anytime` entry in `reference.json` did
  not explicitly state that it is a gym benchmark rather than a paper-reported
  table.
- **Cosmetic:** Generated `__pycache__` directories were present in workspace
  code directories.

## Fixes Applied

- Changed `eval/metrics.py`, `eval/train/evaluate.py`, and
  `eval/test/evaluate.py` to integrate incumbent primal gap over recorded
  restart/iteration effort instead of wall-clock seconds.
- Regenerated `scoring/scores.json`, `scoring/scores_train.json`, and
  `scoring/scores_test.json` from existing JSONL traces.
- Updated `briefing/evaluation.md`, `scoring/reference.json`,
  `scoring/TARGETS.md`, `scoring/EXPERIMENTS.md`, and
  `scoring/CONSTRAINTS.md` to describe the deterministic effort horizon and the
  scaled benchmark clearly.
- Removed generated Python cache directories from workspace code areas.
- Verified all dataset URLs in `scripts/download.sh` with `curl -I -L`.

## Final Judgment

The workspace is ready to serve as a research gym. Improve-mode agents can run
the existing method and baselines, and from-scratch agents can use the
method-agnostic problem, data, evaluation, constraints, and direction documents
without learning the paper's implementation details from those files. The
scoring now rewards incumbent quality over deterministic search effort, final
excess error, and an optimality-proof constraint.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: high
- Key limitation: scaled CPU benchmark on three CP4IM datasets rather than the
  full 25-dataset, depth-6/7 paper protocol.
