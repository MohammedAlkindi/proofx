"""Independent check of a PX-COL-004 output directory.

Imports nothing from study.py. Recomputes window draws, pools, prefixes (step by
step in Python integers), selections, total stopping times (batched halving),
credits, charged work and every aggregate in summary.json, and compares them
exactly. Usage: python verify.py DIR [--corrupt]  (--corrupt checks that a
deliberately wrong stopping time is rejected).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import statistics
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

W, S, K, SEEDS, BUDGETS, OVER = 6_250, 16, 313, 32, (256, 1024), 8
POLICIES = ("uniform", "odd32", "odd64", "halving")


def draw_windows() -> list[int]:
    seed = int.from_bytes(hashlib.sha256(b"PX-COL-004 test windows v1").digest()[:8], "big")
    rng = random.Random(seed)
    excluded = [
        2_097_152,
        33_554_432,
        536_870_912,
        65_303_025,
        54_876_399,
        16_565_133_957,
        807_582_643,
        845_407_870,
        3_158_162,
        56_626_578,
        3_691_221,
        806_530_309,
        52_461_639,
        11_000_919_623,
        983_764_052,
    ]
    out: list[int] = []
    for e in (25, 29, 33, 37):
        got: list[int] = []
        while len(got) < 6:
            lo = rng.randrange(2**e, 2 ** (e + 1) - W * S + 1)
            if all(abs(lo - o) >= W * S for o in excluded + out + got):
                got.append(lo)
        out += sorted(got)
    return out


def tau(n: int) -> int:
    t = 0
    while n != 1:
        if n & 1:
            n = 3 * n + 1
            t += 1
        z = (n & -n).bit_length() - 1
        n >>= z
        t += z
    return t


def prefix(n: int) -> dict[int, tuple[int, int]]:
    x, k, t, out = n, 0, 0, {}
    while t < 64:
        if x == 1:
            break
        if x % 2:
            x, k = 3 * x + 1, k + 1
        else:
            x //= 2
        t += 1
        if t in (16, 32, 64):
            out[t] = (k, t)
    for h in (16, 32, 64):
        out.setdefault(h, (k, t))
    return out


def pools(phase: str, lower: int, seed: int, s: int):
    g = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([0x50584334, int(phase == "test"), lower, seed, s]))
    )
    off = g.choice(W, OVER * 64, replace=False)
    keys = g.random(OVER * 64)
    return [lower + s * W + int(o) for o in off], [float(v) for v in keys]


def choose(policy, pool, keys, q, pf):
    key = dict(zip(pool, keys, strict=True))
    if policy == "uniform":
        return pool[:q], {}
    if policy in ("odd32", "odd64"):
        h = int(policy[3:])
        c = pool[: 4 * q]
        return sorted(c, key=lambda n: (-pf(n)[h][0], key[n]))[:q], {n: pf(n)[h][1] for n in c}
    cur, spent = pool[: OVER * q], {}
    for h, keep in ((16, 4 * q), (32, 2 * q), (64, q)):
        for n in cur:
            spent[n] = pf(n)[h][1]
        cur = sorted(cur, key=lambda n: (-pf(n)[h][0], key[n]))[:keep]
    return cur, spent


def fail(msg: str) -> None:
    print("FAIL:", msg)
    sys.exit(1)


def main(d: Path, corrupt: bool) -> None:
    meta = json.loads((d / "windows.json").read_text())
    phase, wins = meta["phase"], meta["windows"]
    if phase == "test" and wins != draw_windows():
        fail("test windows differ from the seeded draw")
    if phase == "development" and wins != [100_001, 400_001, 800_001]:
        fail("development windows")
    with gzip.open(d / "selections.jsonl.gz", "rb") as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != (d / "selections.sha256").read_text().strip():
        fail("selections hash")
    sels = [json.loads(line) for line in raw.decode().splitlines()]
    with gzip.open(d / "runs.jsonl.gz", "rt") as f:
        runs = [json.loads(line) for line in f]
    summary = json.loads((d / "summary.json").read_text())
    ref = {}
    with gzip.open(d / "reference.csv.gz", "rt") as f:
        for i, line in enumerate(f):
            if i:
                n, t, _lo, _s, lab, fc = line.strip().split(",")
                ref[int(n)] = (int(t), int(lab), Fraction(fc))
    by = {(r["lower"], r["seed"], r["budget"], r["policy"]): r for r in sels}
    rb = {(r["lower"], r["seed"], r["budget"], r["policy"]): r for r in runs}
    if len(by) != len(sels) or len(by) != len(wins) * SEEDS * len(BUDGETS) * len(POLICIES):
        fail("record count")
    checked = 0
    ratios = []
    for lo in wins:
        times = {n: tau(n) for n in range(lo, lo + W * S)}
        if corrupt:
            times[lo + 7] += 1
        cache: dict[int, dict] = {}

        def pf(n, cache=cache):
            if n not in cache:
                cache[n] = prefix(n)
            return cache[n]

        fair, label = {}, set()
        for s in range(S):
            ns = list(range(lo + s * W, lo + (s + 1) * W))
            srt = sorted(ns, key=lambda n: (-times[n], n))
            thr = times[srt[K - 1]]
            above = sum(times[n] > thr for n in ns)
            tie = sum(times[n] == thr for n in ns)
            for n in ns:
                fair[n] = (
                    Fraction(1)
                    if times[n] > thr
                    else (Fraction(K - above, tie) if times[n] == thr else Fraction(0))
                )
            label |= set(srt[:K])
        for n in range(lo, lo + W * S):
            if ref[n] != (times[n], int(n in label), fair[n]):
                fail(f"reference row {n}")
        pl = {(seed, s): pools(phase, lo, seed, s) for seed in range(SEEDS) for s in range(S)}
        agg = {}
        for seed in range(SEEDS):
            for b in BUDGETS:
                q = b // S
                for p in POLICIES:
                    sel, used, screen = [], [], 0
                    for s in range(S):
                        c, sp = choose(p, *pl[(seed, s)], q, pf)
                        sel += c
                        used += [sp.get(n, 0) for n in c]
                        screen += sum(sp.values())
                    r = by[(lo, seed, b, p)]
                    if r["selected"] != sel or r["used"] != used or r["screening"] != screen:
                        fail(f"selection {lo} {seed} {b} {p}")
                    cont = sum(times[n] - u for n, u in zip(sel, used, strict=True))
                    hf = sum((fair[n] for n in sel), Fraction(0))
                    hl = sum(n in label for n in sel)
                    rr = rb[(lo, seed, b, p)]
                    if (
                        rr["screening"],
                        rr["continuation"],
                        Fraction(rr["fair_hits"]),
                        rr["label_hits"],
                    ) != (screen, cont, hf, hl):
                        fail(f"run record {lo} {seed} {b} {p}")
                    a = agg.setdefault((b, p), [Fraction(0), 0, 0])
                    a[0] += hf
                    a[1] += hl
                    a[2] += screen + cont
                    checked += 1
        for b in BUDGETS:
            q = b // S
            rho0 = Fraction(q * K * S, W) / sum(
                Fraction(q * sum(times[n] for n in range(lo + s * W, lo + (s + 1) * W)), W)
                for s in range(S)
            )
            row = summary["windows"][str(lo)][str(b)]
            for p in POLICIES:
                hf, hl, cost = agg[(b, p)]
                exp = {
                    "mean_fair_hits": float(hf / SEEDS),
                    "mean_label_hits": hl / SEEDS,
                    "mean_charged": cost / SEEDS,
                    "fair_yield_ratio": float(hf / cost / rho0),
                    "label_yield_ratio": float(Fraction(hl, cost) / rho0),
                }
                if row[p] != exp:
                    fail(f"summary {lo} {b} {p}")
            hr = float(
                (agg[(b, "halving")][0] / agg[(b, "halving")][2])
                / (agg[(b, "odd32")][0] / agg[(b, "odd32")][2])
            )
            if row["halving_over_odd32"] != hr:
                fail(f"ratio {lo} {b}")
            if b == 1024:
                ratios.append(hr)
        print(f"window {lo} ok", flush=True)
    prim = summary["primary"]
    if (
        prim["windows"] != len(ratios)
        or prim["halving_wins"] != sum(r > 1 for r in ratios)
        or prim["median_ratio"] != statistics.median(ratios)
    ):
        fail("primary endpoint")
    print(
        f"ALL CHECKS PASSED: {len(wins)} windows, {checked} realizations, {len(ref)} reference rows"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]), "--corrupt" in sys.argv)
