# Hybrid model: random-parity walk until x < 2^CUT, then the exact tau of int(x).
# If the gap closes, the pure model's end phase caused it.
import math
import random
import statistics as st
import sys

CUT = int(sys.argv[1])


def tau(n):
    t = 0
    while n != 1:
        n = n >> 1 if n % 2 == 0 else 3 * n + 1
        t += 1
    return t


memo = {}


def tau_m(n):
    if n not in memo:
        memo[n] = tau(n)
    return memo[n]


rng = random.Random(3)
LC = CUT * math.log(2)


def run(L0, N=40000, reps=300):
    pop = []
    for _ in range(N):
        L = L0
        k = 0
        odd = rng.random() < 0.5
        t = 0
        while t < 32 or L > LC:
            if odd:
                L += math.log(3)
                odd = False
                k += t < 32
            else:
                L -= math.log(2)
                odd = rng.random() < 0.5
            t += 1
        x = max(1, int(math.exp(L)))
        if (x % 2 == 1) != odd:
            x += 1 if x > 1 else 0
        pop.append((k, t + tau_m(x)))
    ts = [p[1] for p in pop]
    Kn = int(0.05008 * N)
    thr = sorted(ts, reverse=True)[Kn - 1]
    above = sum(t > thr for t in ts)
    tie = sum(t == thr for t in ts)
    cr = [(t > thr) + (t == thr) * (Kn - above) / tie for t in ts]
    h = []
    for _ in range(reps):
        pool = rng.sample(range(N), 256)
        pool.sort(key=lambda i: (-pop[i][0], rng.random()))
        h.append(sum(cr[i] for i in pool[:64]))
    return st.mean(h) / (64 * Kn / N), st.pstdev(ts), st.mean(ts)


for e in (23, 27, 31):
    en, sd, mt = run(math.log(2**e * 1.5))
    print(
        "cut",
        CUT,
        "octave",
        e,
        "hybrid enrich",
        round(en, 3),
        "sd",
        round(sd, 1),
        "mean",
        round(mt, 1),
        flush=True,
    )
