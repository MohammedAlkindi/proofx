# Same as gap.py but each "stratum" is 6250 inputs drawn at random from a wide range [2^e, 2^e*1.05),
# so inputs rarely share trajectory suffixes. If the gap vanishes, it came from window clustering.
import math
import random
import statistics as st
import sys

import numpy as np

sys.path.insert(0, sys.argv[2])
import gap as g

rng = random.Random(99)
nrng = np.random.default_rng(5)
out = []
for w in range(int(sys.argv[1])):
    e = [23, 27, 31][w % 3]
    lo = 2**e
    span = int(lo * 0.05)
    hits = []
    sds = []
    for s in range(g.S):
        ns = np.array(sorted(rng.sample(range(lo, lo + span), g.W)), dtype=np.uint64)
        t, k = g.tau_k(ns)
        cr = g.credit(t)
        sds.append(t.std())
        hits.append(np.mean([g.select_hits(k, cr, nrng) for _ in range(32)]))
    obs = sum(hits) / (g.S * 64 * g.K / g.W)
    me, msd = g.model_enrich(math.log(lo * 1.025), rng)
    out.append(obs / me)
    print(
        e,
        round(obs, 3),
        round(me, 3),
        "sd obs",
        round(float(np.mean(sds)), 1),
        "sd model",
        round(float(msd), 1),
        flush=True,
    )
print("scattered ratio obs/model mean", round(st.mean(out), 3), "sd", round(st.pstdev(out), 3))
