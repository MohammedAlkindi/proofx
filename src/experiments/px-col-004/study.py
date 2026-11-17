"""PX-COL-004: successive-halving prefix screening versus single-stage odd count.

Ordinary map C(n) = n/2 or 3n+1, stopping at the first 1. Exact integers.
See docs/experiments/px-col-004-protocol.md. Usage:

    python study.py development --output DIR
    python study.py test --output DIR --freeze-commit SHA

The run writes selections (and their hash) before it computes any total
stopping time, then writes labels, costs and the summary.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import statistics
from fractions import Fraction
from pathlib import Path

import numpy as np

WIDTH = 6_250
STRATA = 16
TARGETS = 313
WINDOW = WIDTH * STRATA
SEEDS = range(32)
BUDGETS = (256, 1024)
OVERSAMPLE = 8
HORIZONS = (16, 32, 64)
POLICIES = ("uniform", "odd32", "odd64", "halving")
TAG = 0x50584334  # "PXC4"

DEVELOPMENT = (100_001, 400_001, 800_001)
# Windows whose labels were already inspected and must not overlap the test set:
# PX-COL-002 fresh windows and the exploratory windows of the 2026-11 review.
EXCLUDED = (
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
)
TEST_OCTAVES = (25, 29, 33, 37)
PER_OCTAVE = 6


def test_windows() -> list[int]:
    """Seeded draw of 24 test windows, fixed before any label exists."""
    seed = int.from_bytes(hashlib.sha256(b"PX-COL-004 test windows v1").digest()[:8], "big")
    rng = random.Random(seed)
    chosen: list[int] = []
    for e in TEST_OCTAVES:
        got: list[int] = []
        while len(got) < PER_OCTAVE:
            lo = rng.randrange(2**e, 2 ** (e + 1) - WINDOW + 1)
            taken = list(EXCLUDED) + chosen + got
            if all(abs(lo - other) >= WINDOW for other in taken):
                got.append(lo)
        chosen.extend(sorted(got))
    return chosen


def windows(phase: str) -> list[int]:
    if phase == "development":
        return list(DEVELOPMENT)
    if phase == "test":
        return test_windows()
    raise ValueError("unknown phase")


def pool_and_keys(phase: str, lower: int, seed: int, stratum: int) -> tuple[list[int], list[float]]:
    """Ordered proposal pool of OVERSAMPLE * q_max distinct inputs and tie-break keys."""
    q_max = max(BUDGETS) // STRATA
    gen = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([TAG, int(phase == "test"), lower, seed, stratum]))
    )
    offsets = gen.choice(WIDTH, OVERSAMPLE * q_max, replace=False)
    keys = gen.random(OVERSAMPLE * q_max)
    base = lower + stratum * WIDTH
    return [base + int(o) for o in offsets], [float(k) for k in keys]


SAFE = np.uint64((2**64 - 2) // 3)


def prefix_features(ns: np.ndarray) -> dict[int, tuple[int, ...]]:
    """For each n: (k16, u16, k32, u32, k64, u64); k = odd steps, u = steps run (< h if 1 reached)."""
    x = ns.astype(np.uint64)
    k = np.zeros(len(x), np.int64)
    u = np.zeros(len(x), np.int64)
    big = np.zeros(len(x), bool)
    snaps = {}
    for step in range(64):
        act = (x != 1) & ~big
        v = x[act]
        odd = (v & np.uint64(1)) == 1
        over = odd & (v > SAFE)
        if over.any():
            idx = np.nonzero(act)[0][over]
            big[idx] = True
            act = (x != 1) & ~big
            v = x[act]
            odd = (v & np.uint64(1)) == 1
        x[act] = np.where(odd, v * np.uint64(3) + np.uint64(1), v >> np.uint64(1))
        k[act] += odd
        u[act] += 1
        if step + 1 in HORIZONS:
            snaps[step + 1] = (k.copy(), u.copy())
    out = {}
    for i, n in enumerate(ns.tolist()):
        if big[i]:
            out[n] = _py_prefix(n)
        else:
            out[n] = tuple(int(a) for h in HORIZONS for a in (snaps[h][0][i], snaps[h][1][i]))
    return out


def _py_prefix(n: int) -> tuple[int, ...]:
    x, k, t, res = n, 0, 0, []
    for h in HORIZONS:
        while t < h and x != 1:
            if x & 1:
                x, k = 3 * x + 1, k + 1
            else:
                x >>= 1
            t += 1
        res += [k, t]
    return tuple(res)


def total_stopping_time(n: int) -> int:
    t = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        t += 1
    return t


def stopping_times(ns: np.ndarray) -> np.ndarray:
    """Vectorized exact total stopping times; overflow candidates finish in Python ints."""
    x = ns.astype(np.uint64)
    t = np.zeros(len(x), np.int64)
    big = np.zeros(len(x), bool)
    while True:
        act = (x != 1) & ~big
        if not act.any():
            break
        v = x[act]
        odd = (v & np.uint64(1)) == 1
        over = odd & (v > SAFE)
        if over.any():
            idx = np.nonzero(act)[0][over]
            big[idx] = True
            continue
        x[act] = np.where(odd, v * np.uint64(3) + np.uint64(1), v >> np.uint64(1))
        t[act] += 1
    for i in np.nonzero(big)[0]:
        t[i] += total_stopping_time(int(x[i]))
    return t


def select(
    policy: str, pool: list[int], keys: list[float], q: int, feat
) -> tuple[list[int], dict[int, int]]:
    """Return selected inputs and, for every screened input, the prefix steps it consumed."""
    key = dict(zip(pool, keys, strict=True))
    if policy == "uniform":
        return pool[:q], {}
    if policy in ("odd32", "odd64"):
        h = 32 if policy == "odd32" else 64
        j = HORIZONS.index(h)
        cand = pool[: 4 * q]
        ranked = sorted(cand, key=lambda n: (-feat[n][2 * j], key[n]))
        return ranked[:q], {n: feat[n][2 * j + 1] for n in cand}
    if policy == "halving":
        cur = pool[: OVERSAMPLE * q]
        spent: dict[int, int] = {}
        for j, keep in enumerate((4 * q, 2 * q, q)):
            for n in cur:
                spent[n] = feat[n][2 * j + 1]
            cur = sorted(cur, key=lambda n: (-feat[n][2 * j], key[n]))[:keep]
        return cur, spent
    raise ValueError(policy)


def credits(times: dict[int, int], lower: int) -> tuple[dict[int, Fraction], set[int]]:
    """Tie-fair credit (primary) and the PX-COL-002 smaller-input target set (secondary)."""
    fair: dict[int, Fraction] = {}
    label: set[int] = set()
    for s in range(STRATA):
        ns = range(lower + s * WIDTH, lower + (s + 1) * WIDTH)
        ordered = sorted(ns, key=lambda n: (-times[n], n))
        thr = times[ordered[TARGETS - 1]]
        above = sum(1 for n in ns if times[n] > thr)
        tied = sum(1 for n in ns if times[n] == thr)
        share = Fraction(TARGETS - above, tied)
        for n in ns:
            fair[n] = Fraction(1) if times[n] > thr else (share if times[n] == thr else Fraction(0))
        label.update(ordered[:TARGETS])
    return fair, label


def run(phase: str, out: Path, freeze: str | None) -> None:
    out.mkdir(parents=True, exist_ok=False)
    wins = windows(phase)
    (out / "windows.json").write_text(
        json.dumps({"phase": phase, "windows": wins, "freeze_commit": freeze}, indent=1)
    )

    # Pass 1: prefixes and selections only. No total stopping time is computed here.
    selections = []
    for lower in wins:
        feat = prefix_features(np.arange(lower, lower + WINDOW, dtype=np.uint64))
        pools = {
            (seed, s): pool_and_keys(phase, lower, seed, s) for seed in SEEDS for s in range(STRATA)
        }
        for seed in SEEDS:
            for budget in BUDGETS:
                q = budget // STRATA
                for policy in POLICIES:
                    chosen, used, screening = [], [], 0
                    for s in range(STRATA):
                        pool, keys = pools[(seed, s)]
                        sel, spent = select(policy, pool, keys, q, feat)
                        chosen += sel
                        used += [spent.get(n, 0) for n in sel]
                        screening += sum(spent.values())
                    selections.append(
                        {
                            "lower": lower,
                            "seed": seed,
                            "budget": budget,
                            "policy": policy,
                            "selected": chosen,
                            "used": used,
                            "screening": screening,
                        }
                    )
        print(f"selected {lower}", flush=True)
    blob = "\n".join(json.dumps(r, separators=(",", ":")) for r in selections).encode()
    with gzip.open(out / "selections.jsonl.gz", "wb") as f:
        f.write(blob)
    digest = hashlib.sha256(blob).hexdigest()
    (out / "selections.sha256").write_text(digest + "\n")
    print("selections hash", digest, flush=True)

    # Pass 2: labels, then costs and hits.
    summary = {"phase": phase, "windows": {}, "selections_sha256": digest}
    with (
        gzip.open(out / "reference.csv.gz", "wt", newline="") as fref,
        gzip.open(out / "runs.jsonl.gz", "wt") as fruns,
    ):
        w = csv.writer(fref)
        w.writerow(["n", "stopping_time", "lower", "stratum", "label_target", "fair_credit"])
        by_lower: dict[int, list[dict]] = {}
        for r in selections:
            by_lower.setdefault(r["lower"], []).append(r)
        for lower in wins:
            ns = np.arange(lower, lower + WINDOW, dtype=np.uint64)
            times = dict(zip(ns.tolist(), stopping_times(ns).tolist(), strict=True))
            fair, label = credits(times, lower)
            for n in range(lower, lower + WINDOW):
                w.writerow(
                    [n, times[n], lower, (n - lower) // WIDTH, int(n in label), str(fair[n])]
                )
            mean_t = {
                s: Fraction(
                    sum(times[n] for n in range(lower + s * WIDTH, lower + (s + 1) * WIDTH)), WIDTH
                )
                for s in range(STRATA)
            }
            agg = {}
            for r in by_lower[lower]:
                screen = r["screening"]
                cont = sum(times[n] - u for n, u in zip(r["selected"], r["used"], strict=True))
                hf = sum((fair[n] for n in r["selected"]), Fraction(0))
                hl = sum(1 for n in r["selected"] if n in label)
                rec = {k: r[k] for k in ("lower", "seed", "budget", "policy")}
                rec.update(
                    screening=screen,
                    continuation=cont,
                    charged=screen + cont,
                    fair_hits=str(hf),
                    label_hits=hl,
                )
                fruns.write(json.dumps(rec) + "\n")
                a = agg.setdefault((r["budget"], r["policy"]), [Fraction(0), 0, 0])
                a[0] += hf
                a[1] += hl
                a[2] += screen + cont
            win = {}
            for budget in BUDGETS:
                q = budget // STRATA
                exp_hits = Fraction(q * TARGETS * STRATA, WIDTH)
                exp_cost = sum(q * mean_t[s] for s in range(STRATA))
                rho0 = exp_hits / exp_cost
                runs = len(SEEDS)
                row = {"uniform_expected_hits": float(exp_hits)}
                for policy in POLICIES:
                    hf, hl, cost = agg[(budget, policy)]
                    row[policy] = {
                        "mean_fair_hits": float(hf / runs),
                        "mean_label_hits": hl / runs,
                        "mean_charged": cost / runs,
                        "fair_yield_ratio": float(hf / cost / rho0),
                        "label_yield_ratio": float(Fraction(hl, cost) / rho0),
                    }
                hfA, _, cA = agg[(budget, "odd32")]
                hfB, _, cB = agg[(budget, "halving")]
                row["halving_over_odd32"] = float((hfB / cB) / (hfA / cA))
                win[str(budget)] = row
            summary["windows"][str(lower)] = win
            print(
                f"labelled {lower}: halving/odd32 at 1024 = {win['1024']['halving_over_odd32']:.3f}",
                flush=True,
            )
    ratios = [summary["windows"][str(lo)]["1024"]["halving_over_odd32"] for lo in wins]
    summary["primary"] = {
        "windows": len(ratios),
        "halving_wins": sum(r > 1 for r in ratios),
        "median_ratio": statistics.median(ratios),
    }
    if phase == "test":
        summary["primary"]["success"] = (
            summary["primary"]["halving_wins"] >= 18 and summary["primary"]["median_ratio"] > 1.05
        )
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary["primary"]), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=("development", "test"))
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--freeze-commit")
    a = ap.parse_args()
    if a.phase == "test" and not a.freeze_commit:
        ap.error("test requires --freeze-commit")
    run(a.phase, a.output, a.freeze_commit)
