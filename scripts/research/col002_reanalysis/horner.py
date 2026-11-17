import collections
def run(n, h):
    x = n; k = 0; m = 0; c = 0
    for _ in range(h):
        if x & 1:
            c = 3 * c + 2 ** m; x = 3 * x + 1; k += 1
        else:
            x //= 2; m += 1
    assert 2 ** m * x == 3 ** k * n + c
    return k, m, c
for h in (8, 10, 12):
    best = collections.defaultdict(int)
    for n in range(1, 2 ** (h + 3)):
        k, m, c = run(n, h); best[(k, m)] = max(best[(k, m)], c)
    bad = 0; tight_all = True
    for (k, m), c in sorted(best.items()):
        b1 = 2 ** (m + 1 - k) * (3 ** k - 2 ** k) if k >= 1 else 0
        if c > b1 or 2 * c > (3 ** k - 1) * 2 ** m: bad += 1
        tight_all &= (c == b1)
        if h == 10:
            print(h, k, m, 'max c', c, 'sharp', b1, 'proofx', (3 ** k - 1) * 2 ** m // 2)
    print('h', h, 'violations', bad, 'sharp bound attained for every (k,m):', tight_all)
