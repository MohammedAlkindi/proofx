# Exploratory wall-time comparison: vectorized odd32 vs halving vs uniform, whole window per call.
import statistics as st
import sys
import time

import numpy as np

SAFE = np.uint64((2**64 - 2) // 3)
W, S = 6250, 16


def advance(x, k, u, steps):
    """Advance uint64 values `steps` ordinary steps (stopping at 1); count odd steps. Returns big mask."""
    big = np.zeros(len(x), bool)
    for _ in range(steps):
        act = (x != 1) & ~big
        if not act.any():
            break
        v = x[act]
        odd = (v & np.uint64(1)) == 1
        over = odd & (v > SAFE)
        if over.any():
            big[np.nonzero(act)[0][over]] = True
            act = (x != 1) & ~big
            v = x[act]
            odd = (v & np.uint64(1)) == 1
        x[act] = np.where(odd, v * np.uint64(3) + np.uint64(1), v >> np.uint64(1))
        k[act] += odd
        u[act] += 1
    return big


def finish(x, u):
    """Run to 1; returns total steps (u + remaining). Python fallback for overflow."""
    t = u.copy()
    big = np.zeros(len(x), bool)
    while True:
        act = (x != 1) & ~big
        if not act.any():
            break
        v = x[act]
        odd = (v & np.uint64(1)) == 1
        over = odd & (v > SAFE)
        if over.any():
            big[np.nonzero(act)[0][over]] = True
            continue
        x[act] = np.where(odd, v * np.uint64(3) + np.uint64(1), v >> np.uint64(1))
        t[act] += 1
    for i in np.nonzero(big)[0]:
        n = int(x[i])
        c = 0
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            c += 1
        t[i] += c
    return t


def run(policy, lo, rng, q=64, F=8, depths=(16, 32, 64)):
    # pools: per stratum distinct uniform offsets
    pools = [lo + s * W + rng.choice(W, F * q, replace=False) for s in range(S)]
    keys = rng.random((S, F * q))
    t0 = time.perf_counter()
    if policy == "uniform":
        sel = np.concatenate([p[:q] for p in pools]).astype(np.uint64)
        finish(sel.copy(), np.zeros(len(sel), np.int64))
    else:
        if policy == "odd32":
            cand = np.concatenate([p[: 4 * q] for p in pools]).astype(np.uint64)
            kk = np.concatenate([k[: 4 * q] for k in keys])
            strat = np.repeat(np.arange(S), 4 * q)
            x = cand.copy()
            k = np.zeros(len(x), np.int64)
            u = np.zeros(len(x), np.int64)
            advance(
                x, k, u, 32
            )  # big ones: treat as continuing (rare); exactness not needed for timing
            order = np.lexsort((kk, -k, strat))
            keep = []
            for s in range(S):
                idx = order[strat[order] == s][:q]
                keep.append(idx)
            idx = np.concatenate(keep)
        else:
            cand = np.concatenate([p for p in pools]).astype(np.uint64)
            kk = keys.reshape(-1)
            strat = np.repeat(np.arange(S), F * q)
            x = cand.copy()
            k = np.zeros(len(x), np.int64)
            u = np.zeros(len(x), np.int64)
            idx = np.arange(len(x))
            done = 0
            per = F * q
            for d in depths:
                sub = idx
                xs, ks, us = x[sub], k[sub], u[sub]
                advance(xs, ks, us, d - done)
                x[sub], k[sub], u[sub] = xs, ks, us
                done = d
                per //= 2
                order = sub[np.lexsort((kk[sub], -k[sub], strat[sub]))]
                idx = np.concatenate([order[strat[order] == s][:per] for s in range(S)])
        finish(x[idx].copy(), u[idx].copy())
    return time.perf_counter() - t0


if __name__ == "__main__":
    lowers = [int(a) for a in sys.argv[1:]] or [100_001, 400_001, 800_001]
    for lo in lowers:
        times = {p: [] for p in ("uniform", "odd32", "halving")}
        for seed in range(12):
            for p in (
                ("uniform", "odd32", "halving") if seed % 2 else ("halving", "odd32", "uniform")
            ):
                times[p].append(run(p, lo, np.random.default_rng(seed)))
        print(lo, {p: round(st.median(v) * 1000, 1) for p, v in times.items()}, "ms median")
