#!/bin/bash
# Job script (CPU). Rebuilds the benchmark instances if missing, scores every
# registered solver on the train and held-out test slices, then runs the
# hardening probes (better/weaker variants and shortcuts) through the test.
# Test-side per-run logs go to outputs/ (gitignored) so that no test instance
# detail reaches the job's stdout.

set -euo pipefail

cd /home/user
mkdir -p outputs scoring
t0=$(date +%s)
stamp() { echo "[$(( $(date +%s) - t0 ))s] $*"; }

if [ ! -s eval/train/instances.json ]; then
  stamp "building train instances"
  python -m eval.train.build_instances > outputs/build_train.log 2>&1
fi
if [ ! -s eval/test/instances.json ]; then
  stamp "building test instances"
  python -m eval.test.build_instances > outputs/build_test.log 2>&1
fi
stamp "instances: train $(python -c 'import json;print(len(json.load(open("eval/train/instances.json"))["instances"]))'), test $(python -c 'import json;print(len(json.load(open("eval/test/instances.json"))["instances"]))')"

stamp "train evaluation (registered solvers)"
python -m eval.train.evaluate --verbose --runs-dir outputs/runs_train > outputs/train_eval.log 2>&1
cp scoring/scores_train.json scoring/scores.json

stamp "test evaluation (registered solvers)"
python -m eval.test.evaluate --verbose --runs-dir outputs/runs_test > outputs/test_eval.log 2>&1

stamp "test evaluation of hardening probes"
python -m eval.test.evaluate --verbose --registry redteam/hardening/solvers.json \
  --registry redteam/hardening/solvers_dup.json \
  --out redteam/hardening/scores_test_probes.json --runs-dir outputs/runs_test_probes \
  > outputs/test_probes.log 2>&1

stamp "train evaluation of the better / weaker variants"
python -m eval.train.evaluate --verbose --registry redteam/hardening/solvers.json \
  --solvers ca_discrepancy_kdp ca_discrepancy_nocache shortcut_bruteforce_lattice \
  --out redteam/hardening/scores_train_probes.json --runs-dir outputs/runs_train_probes \
  > outputs/train_probes.log 2>&1

stamp "summary"
python - <<'EOF'
import json
for path in ["scoring/scores_train.json", "scoring/scores_test.json",
             "redteam/hardening/scores_test_probes.json", "redteam/hardening/scores_train_probes.json"]:
    d = json.load(open(path))
    print("==", path)
    for exp, v in d["experiments"].items():
        print(" ", exp, "instances", v.get("instances"))
        for m, r in sorted(v["results"].items(), key=lambda kv: kv[1]["avg_primal_gap_integral"]):
            print(f"    {m:30s} PI={r['avg_primal_gap_integral']:.4f} final_gap={r['avg_final_primal_gap']:.4f}  {d['status'].get(m, '')[:90]}")
EOF
python validate.py || true
stamp "done"
