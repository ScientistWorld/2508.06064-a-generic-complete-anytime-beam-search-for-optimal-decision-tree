# Problem Definition

## Research Question

Given a binary classification dataset over boolean features, a maximum tree
depth and a minimum leaf support, find a decision tree with the minimum number
of misclassified training examples. The problem is NP-hard. How can a solver
return good trees early, improve them steadily, and still be able to certify the
optimum when given enough effort?

## Why It Matters

Optimal decision trees are smaller and more accurate than greedily induced ones
and remain interpretable. Exact solvers guarantee optimality but are often
interrupted before they finish, and then return whatever tree they currently
hold. A solver whose current tree is good at every moment (good *anytime*
behaviour) is far more useful in practice than one that is only good once it
completes, provided it does not give up the ability to prove optimality.

## Setting Used Here

The data are the CP4IM binary benchmark datasets used by the original study.
Each benchmark instance is a hidden random subsample of one dataset: a random
60% of its rows (at most 1000) and 40 random features, with feature identities
permuted and polarities randomly flipped. Trees have maximum depth 4 or 5 and
minimum leaf support 1. A solver never sees the data. It obtains class counts
from the evaluator, which charges one unit of effort per count, and the budget
is far smaller than the number of counts that exhaustive search would need.

## Success Criteria

- The solver's current tree is close to the optimum throughout the effort
  budget, not only at the end.
- The final tree is close to the optimum.
- The solver remains complete: when the budget exceeds the size of the whole
  search space it certifies the optimal tree.
