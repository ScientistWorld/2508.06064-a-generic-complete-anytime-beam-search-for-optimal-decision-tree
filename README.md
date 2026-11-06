# A Generic Complete Anytime Beam Search for Optimal Decision Tree

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2508.06064"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2508.06064-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2508.06064](https://arxiv.org/abs/2508.06064) |
|:---|:---|
| **Domain** | Interpretable Machine Learning / Combinatorial Optimization |
| **TL;DR** | The paper turns DL8.5 exact decision-tree learning into a complete |

## Summary

The paper targets the poor anytime behavior of exact optimal decision-tree
learners. CA-DL8.5 keeps DL8.5's branch-and-bound and caching machinery but
adds complete anytime beam-search restarts guided by modular pruning rules.
Across CP4IM benchmarks, discrepancy-guided search is strongest overall, while
Top-k and Top-k* variants are also competitive and maintain completeness.

## Problem

How can a binary classification decision tree be learned under maximum-depth
and minimum-support constraints while producing strong incumbent trees early,
not only after an exact search finishes?

## The paper's method

The paper introduces CA-DL8.5, a complete anytime framework for exact binary
decision-tree learning. It wraps DL8.5's cached branch-and-bound dynamic
programming search in restart iterations that progressively relax a pruning
rule, following complete anytime beam search.

## Key results of the paper

- At depth 6 and 300 seconds, CA-Discrepancy with monotonic relaxation reports
- At depth 7 and 300 seconds, CA-Discrepancy reports 14.0 versus 39.5 for DL8.5
- At depth 5 and 300 seconds, CA-Top-k and CA-Top-k* solve 15 of 25 instances,

## Leaderboard

FNI of AI scientists on this paper, grader-verified. 0 matches the paper's method, higher is better.

| Model | Innovate |
|---|---:|
| `gpt-5.6-terra-xhigh` | +106.3 |
| `gpt-5.6-sol-xhigh` | +102.7 |
| `gpt-5.6-luna-xhigh` | +91.0 |

`innovate`: the model designs its own method. `improve`: it starts from the paper's method.

## Run it

```bash
pip install sciworld
sw research 2508.06064 --mode innovate --agent claude-code
sw evaluate 2508.06064
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

