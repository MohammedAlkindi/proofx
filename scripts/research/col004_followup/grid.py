# Schedule grid on the PX-COL-004 test windows (development data after that study).
# Usage: python -I grid.py   (several minutes)
import gzip
import statistics as st
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src" / "experiments" / "px-col-004"))
import study as s4  # noqa: E402

H = (8, 16, 32, 64, 128)
SAFE = np.uint64((2**64 - 2) // 3)


def feats(ns):
    x = ns.astype(np.uint64)
    k = np.zeros(len(x), np.int64)
    u = np.zeros(len(x), np.int64)
    big = np.zeros(len(x), bool)
    snaps = {}
    for step in range(max(H)):
        act = (x != 1) & ~big
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
        if step + 1 in H:
            snaps[step + 1] = (k.copy(), u.copy())
    out = {}
    for i, n in enumerate(ns.tolist()):
        if big[i]:
            xx, kk, t, r = n, 0, 0, {}
            for h in H:
                while t < h and xx != 1:
                    if xx & 1:
                        xx, kk = 3 * xx + 1, kk + 1
                    else:
                        xx >>= 1
                    t += 1
                r[h] = (kk, t)
            out[n] = r
        else:
            out[n] = {h: (int(snaps[h][0][i]), int(snaps[h][1][i])) for h in H}
    return out


def sched_select(pool, keys, q, F, depths, f):
    key = dict(zip(pool, keys, strict=True))
    cur = pool[: F * q]
    spent = {}
    keep = F * q
    for d in depths:
        keep //= 2
        for n in cur:
            spent[n] = f[n][d][1]
        cur = sorted(cur, key=lambda n: (-f[n][d][0], key[n]))[:keep]
    return cur, spent


def single(pool, keys, q, h, f, F=4):
    key = dict(zip(pool, keys, strict=True))
    c = pool[: F * q]
    return sorted(c, key=lambda n: (-f[n][h][0], key[n]))[:q], {n: f[n][h][1] for n in c}


SCHEDS = {
    "F4 16-32": (4, (16, 32)),
    "F4 32-64": (4, (32, 64)),
    "F4 16-64": (4, (16, 64)),
    "F4 32-128": (4, (32, 128)),
    "F8 16-32-64": (8, (16, 32, 64)),
    "F8 8-16-32": (8, (8, 16, 32)),
    "F8 16-32-128": (8, (16, 32, 128)),
    "F8 16-64-128": (8, (16, 64, 128)),
    "F8 32-64-128": (8, (32, 64, 128)),
    "F16 8-16-32-64": (16, (8, 16, 32, 64)),
    "F16 16-32-64-128": (16, (16, 32, 64, 128)),
    "F16 8-16-32-128": (16, (8, 16, 32, 128)),
}
ref_path = ROOT / "src" / "experiments" / "px-col-004" / "test" / "reference.csv.gz"
tau = {}
fair = {}
with gzip.open(ref_path, "rt") as fh:
    for i, line in enumerate(fh):
        if i:
            n, t, lo, s, lab, fc = line.strip().split(",")
            tau[int(n)] = int(t)
            fair[int(n)] = Fraction(fc)
wins = s4.test_windows()
q = 64
res = {name: [] for name in list(SCHEDS) + ["odd32"]}
for lo in wins:
    f = feats(np.arange(lo, lo + s4.WINDOW, dtype=np.uint64))
    agg = {name: [Fraction(0), 0] for name in res}
    for seed in range(32):
        for st_ in range(16):
            g = np.random.Generator(
                np.random.PCG64(np.random.SeedSequence([0x50584335, 0, lo, seed, st_]))
            )
            pool = [lo + st_ * 6250 + int(o) for o in g.choice(6250, 16 * q, replace=False)]
            keys = [float(v) for v in g.random(16 * q)]
            for name, (F, d) in SCHEDS.items():
                if F * q > len(pool):
                    continue
                sel, sp = sched_select(pool, keys, q, F, d, f)
                agg[name][0] += sum((fair[n] for n in sel), Fraction(0))
                agg[name][1] += sum(sp.values()) + sum(tau[n] - sp[n] for n in sel)
            sel, sp = single(pool, keys, q, 32, f)
            agg["odd32"][0] += sum((fair[n] for n in sel), Fraction(0))
            agg["odd32"][1] += sum(sp.values()) + sum(tau[n] - sp[n] for n in sel)
    base = agg["odd32"][0] / agg["odd32"][1]
    for name in SCHEDS:
        if agg[name][1]:
            res[name].append(float((agg[name][0] / agg[name][1]) / base))
    print(lo, {k: round(v[-1], 3) for k, v in res.items() if v and k != "odd32"}, flush=True)
print("MEDIAN ratio vs odd32 over", len(wins), "windows")
for name, v in sorted(res.items(), key=lambda kv: -st.median(kv[1]) if kv[1] else 0):
    if v:
        print(f"{name:20s} median {st.median(v):.3f} min {min(v):.3f} wins {sum(x > 1 for x in v)}")
