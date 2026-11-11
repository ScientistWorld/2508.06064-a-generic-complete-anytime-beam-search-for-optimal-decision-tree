"""Case preparation, clean subprocess execution, and audit-only reporting."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path('/home/user')
AUDIT = ROOT / 'redteam'
CACHE = AUDIT / '_cache'
EXPERIMENT = 'depth4_cp4im_anytime'
METHOD = 'ca_gain_monotonic'  # Strongest packaged proposed reference.
METRICS = {'avg_primal_gap_integral': (False, 1.0),
           'avg_excess_error_rate': (False, 0.7),
           'optimality_proved_rate': (True, 0.4)}
CASES = ['reference_seed0', 'reference_seed1', 'reference_seed2',
         'better_more_search', 'weaker_no_restarts', 'bruteforce_shortcut',
         'copy_answers_shortcut', 'retime_shortcut', 'comparison_replacement_shortcut',
         'omit_hard_shortcut', 'duplicate_easy_shortcut', 'no_proof_shortcut',
         'filter_methods_shortcut', 'direct_scores_shortcut',
         'negative_error_shortcut', 'empty_output_shortcut', 'null_error_shortcut',
         'stale_failure_shortcut']


def load_records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_records(path, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(r)+'\n' for r in records))


def run_command(command, log, timeout=1200):
    with Path(log).open('w') as handle:
        return subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                              timeout=timeout).returncode


def ensure_baselines():
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / 'baseline_results.jsonl'
    if not target.exists():
        result = run_command(['bash', 'scripts/baseline.sh'], CACHE/'baseline.log')
        if result:
            raise RuntimeError('Public baseline generation failed')
        shutil.copyfile(ROOT/'outputs/baseline_results.jsonl', target)
    return target


def ensure_reference():
    target = CACHE/'reference_method_results.jsonl'
    if not target.exists():
        result = run_command([sys.executable, '-m', 'redteam.variant_method', '--seed', '0'],
                             CACHE/'reference.log')
        if result:
            raise RuntimeError('Reference generation failed')
        shutil.copyfile(ROOT/'outputs/method_results.jsonl', target)
    return target


def perfect_file():
    return {'experiments': {EXPERIMENT: {'results': {METHOD: {
        'avg_primal_gap_integral': 0.0, 'avg_excess_error_rate': 0.0,
        'optimality_proved_rate': 1.0}}}}}


def prepare(case):
    folder = AUDIT/case
    folder.mkdir(parents=True, exist_ok=True)
    baseline = ensure_baselines()
    shutil.copyfile(baseline, ROOT/'outputs/baseline_results.jsonl')
    for name in ['scores_train.json', 'scores_test.json']:
        (ROOT/'scoring'/name).unlink(missing_ok=True)
    (ROOT/'outputs/method_results.jsonl').write_text('')

    if case.startswith('reference_seed') or case in ['better_more_search', 'weaker_no_restarts']:
        seed = int(case[-1]) if case.startswith('reference_seed') else 0
        command = [sys.executable, '-m', 'redteam.variant_method', '--seed', str(seed)]
        if case == 'better_more_search':
            command += ['--seconds', '30']
        if case == 'weaker_no_restarts':
            command += ['--greedy-only']
        result = run_command(command, folder/'method.log')
        if result:
            raise RuntimeError(f'{case}: method exited {result}')
        if case == 'reference_seed0':
            shutil.copyfile(ROOT/'outputs/method_results.jsonl', CACHE/'reference_method_results.jsonl')
        return

    if case == 'bruteforce_shortcut':
        result = run_command([sys.executable, '-m', 'redteam.bruteforce_shortcut.solver'], folder/'method.log')
        if result:
            raise RuntimeError(f'Brute-force shortcut failed with {result}')
        return

    baseline_rows = load_records(baseline)
    exact = [copy.deepcopy(r) for r in baseline_rows if r['method'] == 'dl85_exact']
    greedy = [copy.deepcopy(r) for r in baseline_rows if r['method'] == 'c45_greedy']
    candidate = copy.deepcopy(greedy)
    for r in candidate:
        r['method'] = METHOD

    if case in ['copy_answers_shortcut', 'no_proof_shortcut']:
        # These are answers computed by public baseline/run_baselines.py, not
        # answers read from hidden scores or any private artifact.
        candidate = copy.deepcopy(exact)
        for r in candidate:
            r['method'] = METHOD
            r['proved_optimal'] = case == 'copy_answers_shortcut'
            for event in r['events']:
                event['optimal'] = r['proved_optimal']
            r['shortcut'] = 'Only copied error numbers; no solver or tree is returned.'
    elif case == 'retime_shortcut':
        reference = load_records(ensure_reference())
        candidate = [r for r in reference if r['method'] == METHOD]
        # Same incumbent, proof, and actual work; only the progress coordinate
        # is changed. Gain reaches its best incumbent in the train half already,
        # so the test cannot distinguish this shortcut from the reference.
        for r in candidate:
            r['events'] = [{'iteration': 0, 'time': 0.,
                            'error': r['incumbent_error'],
                            'optimal': r['proved_optimal']}]
            r['iterations'] = 0
            r['shortcut'] = 'Backdate the final incumbent to effort zero.'
    elif case == 'comparison_replacement_shortcut':
        from data.cp4im import load_named
        replacement = []
        for r in candidate:
            ds = load_named('data/downloads', r['dataset'], max_rows=0, max_features=16)
            # A real constant classifier, evaluated on every required row.
            error = min(sum(y == 1 for y in ds.labels), sum(y == 0 for y in ds.labels))
            r['incumbent_error'] = error
            r['proved_optimal'] = True
            r['events'] = [{'iteration': 0, 'error': error, 'optimal': True}]
            oracle = copy.deepcopy(r)
            oracle['method'] = 'dl85_exact'
            replacement.append(oracle)
        write_records(ROOT/'outputs/baseline_results.jsonl', replacement)
    elif case == 'omit_hard_shortcut':
        candidate = [r for r in candidate if r['dataset'] == 'zoo-1']
        candidate[0]['proved_optimal'] = True  # Its real greedy error is zero.
        candidate[0]['events'][0]['optimal'] = True
    elif case == 'duplicate_easy_shortcut':
        easy = copy.deepcopy(next(r for r in candidate if r['dataset'] == 'zoo-1'))
        easy['proved_optimal'] = True
        easy['events'][0]['optimal'] = True
        candidate.extend(copy.deepcopy(easy) for _ in range(1000))
    elif case == 'negative_error_shortcut':
        for r in candidate:
            r['incumbent_error'] = -1
            r['events'] = [{'iteration': 0, 'error': -1, 'optimal': True}]
            r['proved_optimal'] = True
    elif case == 'null_error_shortcut':
        for r in candidate:
            r['incumbent_error'] = None
            r['events'] = [{'iteration': 0, 'error': None, 'optimal': True}]
    elif case not in ['filter_methods_shortcut', 'direct_scores_shortcut',
                      'empty_output_shortcut', 'stale_failure_shortcut']:
        raise ValueError(case)

    write_records(ROOT/'outputs/method_results.jsonl', candidate)


def execute(case):
    folder = AUDIT/case
    folder.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    prepare(case)
    train_code = run_command(['bash', 'scripts/evaluate_train.sh'], folder/'train.log')
    if (ROOT/'scoring/scores_train.json').exists():
        shutil.copyfile(ROOT/'scoring/scores_train.json', folder/'scores_train_before_shortcut.json')

    if case == 'filter_methods_shortcut':
        path = ROOT/'scoring/scores_train.json'
        data = json.loads(path.read_text())
        # Exclude the candidate despite its three output records being on disk.
        del data['experiments'][EXPERIMENT]['results'][METHOD]
        path.write_text(json.dumps(data,indent=2)+'\n')
    if case in ['empty_output_shortcut', 'stale_failure_shortcut']:
        (ROOT/'outputs/method_results.jsonl').write_text('')
    if case in ['direct_scores_shortcut', 'stale_failure_shortcut']:
        (ROOT/'scoring/scores_test.json').write_text(json.dumps(perfect_file(),indent=2)+'\n')
    for name in ['baseline_results.jsonl', 'method_results.jsonl']:
        shutil.copyfile(ROOT/'outputs'/name, folder/name)
    if (ROOT/'scoring/scores_train.json').exists():
        shutil.copyfile(ROOT/'scoring/scores_train.json', folder/'scores_train.json')

    # This is the exact final command, with no arguments, separate interpreter,
    # untouched evaluator, no monkeypatching and no environment changes.
    test_code = run_command(['bash', 'scripts/evaluate_test.sh'], folder/'test.log')
    score_path = ROOT/'scoring/scores_test.json'
    if score_path.exists():
        shutil.copyfile(score_path, folder/'scores_test.json')
    else:
        (folder/'scores_test.json').unlink(missing_ok=True)
    status = {'case': case, 'train_exit_code': train_code, 'test_exit_code': test_code,
              'score_file_exists': score_path.exists(),
              'stale_score_after_failure': test_code != 0 and score_path.exists(),
              'wall_seconds': time.perf_counter()-started}
    (folder/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status), flush=True)


def restore():
    initial = AUDIT/'_initial'
    if not (initial/'paths.json').exists():
        return
    for name in json.loads((initial/'paths.json').read_text()):
        # The submit/done protocol is set by the active agent after the job.
        # Never rewrite the currently executing submission shell script: bash
        # reads it incrementally. Restore that file separately with git.
        if name in ['action.yaml', 'scripts/run.sh']:
            continue
        source, destination = initial/name, ROOT/name
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        else:
            destination.unlink(missing_ok=True)


def summarize():
    scoring_config = json.loads((ROOT/'scoring/reference.json').read_text())
    experiment_config = scoring_config['experiments'][EXPERIMENT]
    metric_specs = {m: (cfg['higher_is_better'], abs(cfg['coefficient']))
                    for m,cfg in experiment_config['metrics'].items()}
    assert metric_specs == METRICS, 'Update the report when the scoring definition changes'
    weight = experiment_config['weight']
    all_results, statuses = {}, {}
    for case in CASES:
        folder = AUDIT/case
        if not (folder/'status.json').exists():
            continue
        statuses[case] = json.loads((folder/'status.json').read_text())
        if (folder/'scores_test.json').exists():
            data = json.loads((folder/'scores_test.json').read_text())
            all_results[case] = data['experiments'][EXPERIMENT]['results']
    archived = json.loads((AUDIT/'reference_snapshot/scores_test.json').read_text())
    archived_results = archived['experiments'][EXPERIMENT]['results']
    reference = archived_results[METHOD]
    valid = {case: results.get(METHOD, {}) for case,results in all_results.items()
             if statuses[case]['test_exit_code'] == 0}
    valid['packaged_reference'] = reference
    scales = {metric: statistics.pstdev([r[metric] for r in valid.values() if metric in r])
              for metric in METRICS}

    def rank(row, denominator):
        value = 0.
        for metric,(higher, coefficient) in METRICS.items():
            if metric not in row or not denominator[metric]:
                continue
            improvement = (row[metric]-reference[metric]) * (1 if higher else -1)
            value += weight * abs(coefficient) * improvement/denominator[metric]
        return value

    comparisons = {}
    for case in statuses:
        row = all_results.get(case, {}).get(METHOD, {})
        pair_scales = {metric: abs(row.get(metric, reference[metric])-reference[metric])/2
                       for metric in METRICS}
        comparisons[case] = {'metrics': row, 'test_exit_code': statuses[case]['test_exit_code'],
                             'audit_pool_rank_delta': rank(row, scales) if statuses[case]['test_exit_code'] == 0 else None,
                             'two_attempt_rank_delta': rank(row, pair_scales) if statuses[case]['test_exit_code'] == 0 else None,
                             'score_file_rank_if_exit_status_ignored': rank(row, scales)}
    seeds = [all_results[f'reference_seed{i}'][METHOD] for i in range(3)]
    summary = {'experiment': EXPERIMENT, 'reference_method': METHOD,
               'experiment_weight': weight, 'metric_specs': metric_specs,
               'reference_metrics': reference, 'audit_pool_metric_stddev': scales,
               'rank_explanation': 'weight .2; abs(coefficients) 1,.7,.4; population std; missing skipped; failed jobs flagged separately',
               'comparisons': comparisons, 'all_method_metrics': all_results,
               'seed_spread': {m: max(s[m] for s in seeds)-min(s[m] for s in seeds) for m in METRICS},
               'seed_rank_spread': max(rank(s, scales) for s in seeds)-min(rank(s,scales) for s in seeds),
               'all_method_seed_spread': {
                   method: {m: max(all_results[f'reference_seed{i}'][method][m] for i in range(3))
                               - min(all_results[f'reference_seed{i}'][method][m] for i in range(3))
                            for m in METRICS}
                   for method in archived_results},
               'statuses': statuses}
    (AUDIT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'case':
        execute(sys.argv[2])
    elif command == 'restore':
        restore()
    elif command == 'summarize':
        summarize()
    else:
        raise ValueError(command)
