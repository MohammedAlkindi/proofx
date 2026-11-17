import collections
import csv
import gzip
import json
import math
import statistics as st
import sys

B = sys.argv[1]
phase = sys.argv[2] if len(sys.argv) > 2 else "test"
ref = {}
strata = collections.defaultdict(list)
with gzip.open(f"{B}/{phase}/reference.csv.gz", "rt") as f:
    for r in csv.DictReader(f):
        n = int(r["n"])
        t = int(r["stopping_time"])
        key = (int(r["lower"]), int(r["stratum"]))
        ref[n] = (t, int(r["target"]), key)
        strata[key].append((t, n))
thr = {}
for key, v in strata.items():
    v.sort(key=lambda x: (-x[0], x[1]))
    ts = v[312][0]
    above = sum(1 for t, _ in v if t > ts)
    tie = sum(1 for t, _ in v if t == ts)
    thr[key] = (ts, tie, 313 - above)
# exact uniform expected transitions per stratum
mean_t = {k: st.mean(t for t, _ in v) for k, v in strata.items()}
runs = {}
with gzip.open(f"{B}/{phase}/runs.jsonl.gz", "rt") as f:
    for line in f:
        r = json.loads(line)
        if r["budget"] != 1024:
            continue
        fr = 0
        lab = 0
        for rec in r["selected"]:
            t, tg, key = ref[rec[0]]
            ts, tie, tt = thr[key]
            fr += (t > ts) + (t == ts) * tt / tie
            lab += tg
        runs[(r["lower"], r["seed"], r["method"])] = (lab, fr, r["charged_transitions"])
lowers = sorted(set(k[0] for k in runs))
seeds = sorted(set(k[1] for k in runs))


def paired(lo, a, b, idx):
    d = [runs[(lo, s, a)][idx] - runs[(lo, s, b)][idx] for s in seeds]
    m = st.mean(d)
    se = st.stdev(d) / math.sqrt(len(d))
    return m, se, sum(x > 0 for x in d), sum(x < 0 for x in d)


for lo in lowers:
    q = 64
    nstr = [k for k in strata if k[0] == lo]
    exp_h = sum(q * 313 / 6250 for k in nstr)
    exp_t = sum(q * mean_t[k] for k in nstr)
    rho0 = exp_h / exp_t
    print(f"== lower {lo}  uniform rho0 per 1e6 = {rho0 * 1e6:.2f}")
    for m in ["growth", "odd_count", "ascending", "bit_score", "uniform"]:
        H = sum(runs[(lo, s, m)][0] for s in seeds)
        F = sum(runs[(lo, s, m)][1] for s in seeds)
        T = sum(runs[(lo, s, m)][2] for s in seeds)
        print(f"  {m:10s} yield(label)={H / T / rho0:.3f}  yield(tie-fair)={F / T / rho0:.3f}")
    for a, b in [("odd_count", "growth"), ("ascending", "uniform")]:
        for idx, name in [(0, "label"), (1, "tie-fair")]:
            m, se, wins, losses = paired(lo, a, b, idx)
            print(f"  {a}-{b} {name}: mean diff {m:.2f} se {se:.2f} wins {wins} losses {losses}")
