# W3: odd-count enrichment vs random-parity model across exploratory windows.
# Octaves 23, 27, 31 only (kept away from planned PX-COL-004 octaves 25/29/33/37).
import json
import math
import random
import statistics as st
import sys

import numpy as np

W, S, K = 6250, 16, 313
LIM = np.uint64(1) << np.uint64(61)


def tau_k(ns, h=32):
    x = ns.astype(np.uint64).copy()
    t = np.zeros(len(x), np.int64)
    k = np.zeros(len(x), np.int64)
    alive = x != 1
    step = 0
    while alive.any():
        idx = np.nonzero(alive)[0]
        v = x[idx]
        odd = (v & np.uint64(1)) == 1
        v = np.where(odd, v * np.uint64(3) + np.uint64(1), v >> np.uint64(1))
        if (v > LIM).any():
            raise OverflowError
        x[idx] = v
        t[idx] += 1
        if step < h:
            k[idx] += odd
        step += 1
        alive[idx] = v != 1
    return t, k


def credit(taus):
    ts = np.sort(taus)[::-1][K - 1]
    above = (taus > ts).sum()
    tie = (taus == ts).sum()
    return (taus > ts) + (taus == ts) * (K - above) / tie


def select_hits(k, cr, rng, q=64):
    pool = rng.choice(W, 4 * q, replace=False)
    order = sorted(pool, key=lambda i: (-k[i], rng.random()))
    return cr[order[:q]].sum()


def model_enrich(L0, rng, N=40000, reps=300):
    def walk(L, odd):
        t = 0
        while L > 0:
            if odd:
                L += math.log(3)
                odd = False
            else:
                L -= math.log(2)
                odd = rng.random() < 0.5
            t += 1
        return t

    pop = []
    for _ in range(N):
        L = L0
        k = 0
        odd = rng.random() < 0.5
        for _ in range(32):
            if odd:
                L += math.log(3)
                k += 1
                odd = False
            else:
                L -= math.log(2)
                odd = rng.random() < 0.5
        pop.append((k, 32 + walk(L, odd)))
    ks = np.array([p[0] for p in pop])
    ts = np.array([p[1] for p in pop])
    Kn = int(0.05008 * N)
    thr = np.sort(ts)[::-1][Kn - 1]
    above = (ts > thr).sum()
    tie = (ts == thr).sum()
    cr = (ts > thr) + (ts == thr) * (Kn - above) / tie
    hits = []
    for _ in range(reps):
        pool = rng.sample(range(N), 256)
        pool.sort(key=lambda i: (-ks[i], rng.random()))
        hits.append(cr[pool[:64]].sum())
    return st.mean(hits) / (64 * Kn / N), ts.std()


def main():
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 4242)
    nrng = np.random.default_rng(rng.randrange(2**32))
    out = []
    for w in range(int(sys.argv[1])):
        e = [23, 27, 31][w % 3]
        lo = rng.randrange(2**e, 2 ** (e + 1) - W * S)
        hits = []
        sds = []
        slopes = []
        allt = []
        for s in range(S):
            ns = np.arange(lo + W * s, lo + W * (s + 1), dtype=np.uint64)
            t, k = tau_k(ns)
            cr = credit(t)
            allt.append(t)
            sds.append(t.std())
            slopes.append(np.polyfit(k, t, 1)[0])
            hits.append(np.mean([select_hits(k, cr, nrng) for _ in range(32)]))
        obs = sum(hits) / (S * 64 * K / W)
        me, msd = model_enrich(math.log(lo + 50000), rng)
        row = dict(
            octave=e,
            lower=lo,
            obs_enrich=round(obs, 3),
            model_enrich=round(me, 3),
            sd_obs=round(float(np.mean(sds)), 1),
            sd_model=round(float(msd), 1),
            slope=round(float(np.mean(slopes)), 2),
            mean_tau=round(float(np.concatenate(allt).mean()), 1),
            model_mean=round(10.428 * math.log(lo + 50000), 1),
        )
        out.append(row)
        print(json.dumps(row), flush=True)
    r = [o["obs_enrich"] / o["model_enrich"] for o in out]
    print(
        "ratio obs/model: mean",
        round(st.mean(r), 3),
        "sd",
        round(st.pstdev(r), 3),
        "min",
        round(min(r), 3),
        "max",
        round(max(r), 3),
        "n",
        len(r),
    )


if __name__ == "__main__":
    main()
