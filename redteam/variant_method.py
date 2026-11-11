"""Honest extra-search and no-restart controls on the unchanged problem."""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from data.cp4im import load_named
from method.dl85 import BinaryTreeSearch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=3.0)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--greedy-only', action='store_true')
    args = parser.parse_args()
    random.seed(args.seed)
    Path('outputs').mkdir(exist_ok=True)
    with Path('outputs/method_results.jsonl').open('w') as out:
        for name in ['zoo-1', 'vote', 'tic-tac-toe']:
            ds = load_named('data/downloads', name, max_rows=0, max_features=16)
            # Match the public runner's cache sharing/order exactly.
            search = BinaryTreeSearch(ds.rows, ds.labels, ds.features, 4, 1)
            for method, rule, initial in [
                ('ca_discrepancy_monotonic', 'discrepancy', 0.),
                ('ca_topk_star_monotonic', 'topk_star', 1.),
                ('ca_gain_monotonic', 'gain', 0.),
            ]:
                start = time.perf_counter()
                if args.greedy_only:
                    result = search.greedy()
                    payload = {'incumbent_error': result.error,
                               'proved_optimal': False,
                               'events': [{'iteration': 0, 'error': result.error,
                                           'optimal': False, 'time': 0.}],
                               'iterations': 0, 'max_iterations': 16}
                else:
                    payload = search.cadl85(rule=rule, relax='monotonic',
                                            initial=initial, time_limit=args.seconds,
                                            max_iterations=16)
                record = {'dataset': name, 'method': method, 'depth': 4,
                          'minsup': 1, 'n_rows': len(ds.labels), 'n_features': 16,
                          'seed': args.seed, 'wall_seconds': time.perf_counter()-start,
                          **payload}
                out.write(json.dumps(record)+'\n')
                out.flush()


if __name__ == '__main__':
    main()
