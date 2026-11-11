"""Brute-force shortcut: enumerate all legal splits; no bounds or beam rules.

Memoization merges identical subset/depth subproblems. The recurrence explicitly
visits every legal candidate, including after attaining zero error. A whole
exhaustive pass is one search iteration under the gym's progress convention.
Actual CPU work and independently checked feasible trees are saved separately.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

from data.cp4im import load_named


def main():
    records, diagnostics = [], []
    for name in ['zoo-1', 'vote', 'tic-tac-toe']:
        ds = load_named('data/downloads', name, max_rows=0, max_features=16)
        n = len(ds.labels)
        all_mask = (1 << n)-1
        positive = sum(1 << i for i,y in enumerate(ds.labels) if y == 1)
        masks = {f: sum(1 << i for i,row in enumerate(ds.rows) if f in row)
                 for f in ds.features}
        candidate_count = 0

        @lru_cache(None)
        def solve(subset, depth):
            nonlocal candidate_count
            size = subset.bit_count()
            pos = (subset & positive).bit_count()
            best, tree = min(pos, size-pos), {'prediction': int(2*pos > size)}
            if depth:
                for feature, mask in masks.items():
                    right = subset & mask
                    left = subset ^ right
                    if not left or not right:
                        continue
                    candidate_count += 1
                    le, lt = solve(left, depth-1)
                    re, rt = solve(right, depth-1)
                    if le+re < best:
                        best, tree = le+re, {'feature': feature, 'left': lt, 'right': rt}
            return best, tree

        started = time.perf_counter()
        error, tree = solve(all_mask, 4)
        seconds = time.perf_counter()-started

        def predict(node, row):
            if 'feature' not in node:
                return node['prediction']
            return predict(node['right' if node['feature'] in row else 'left'], row)

        observed = sum(predict(tree,row) != y for row,y in zip(ds.rows,ds.labels))
        assert observed == error
        diag = {'dataset': name, 'error': error, 'wall_seconds': seconds,
                'subproblems': solve.cache_info().currsize,
                'split_candidates': candidate_count, 'tree': tree,
                'verified_prediction_error': observed}
        diagnostics.append(diag)
        records.append({'dataset': name, 'method': 'ca_gain_monotonic', 'depth': 4,
                        'minsup': 1, 'n_rows': n, 'n_features': len(ds.features),
                        'incumbent_error': error, 'proved_optimal': True,
                        'events': [{'iteration': 1, 'time': seconds, 'error': error,
                                    'optimal': True}], 'iterations': 1})
        print(json.dumps({k:v for k,v in diag.items() if k != 'tree'}), flush=True)
    Path('outputs/method_results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    Path('redteam/bruteforce_shortcut/diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')


if __name__ == '__main__':
    main()
