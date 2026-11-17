# POST-HOC exploratory scan on PX-COL-002 windows (labels already seen). Not a prospective result.
# Usage: python -I policies.py <extracted bundle dir> test|development
import gzip, csv, sys, collections, statistics as st, random
B=sys.argv[1]; phase=sys.argv[2]
rows=collections.defaultdict(list)
with gzip.open(f'{B}/{phase}/reference.csv.gz','rt') as f:
    for r in csv.DictReader(f): rows[(int(r['lower']),int(r['stratum']))].append((int(r['n']),int(r['stopping_time'])))
tau={}; credit={}
for key,v in rows.items():
    srt=sorted(v,key=lambda x:-x[1]); ts=srt[312][1]; above=sum(t>ts for _,t in v); tie=sum(t==ts for _,t in v); w=(313-above)/tie
    for n,t in v: tau[n]=t; credit[n]=(t>ts)+(t==ts)*w
cache={}
def pref(n,h):
    key=(n,h)
    if key in cache: return cache[key]
    x=n;k=0;i=0
    while i<h and x!=1:
        if x&1: x=3*x+1;k+=1
        else: x>>=1
        i+=1
    cache[key]=(k,i); return k,i
def odd(n,h,pool,q,rng):
    sc=[(pref(n_,h),rng.random(),n_) for n_ in pool]
    cost=sum(s[0][1] for s in sc); sc.sort(key=lambda s:(-s[0][0],s[1]))
    sel=[s[2] for s in sc[:q]]; cost+=sum(tau[n_]-pref(n_,h)[1] for n_ in sel); return sel,cost
def halving(pool,q,stages,rng):
    # stages: list of (h, keep) ; pool size = stages[0] count
    cur=pool; spent={n_:0 for n_ in pool}
    for h,keep in stages:
        sc=[]
        for n_ in cur:
            k,used=pref(n_,h); spent[n_]=used; sc.append((-k,rng.random(),n_))
        sc.sort(); cur=[s[2] for s in sc[:keep]]
    sel=cur; cost=sum(spent.values())+sum(tau[n_]-spent[n_] for n_ in sel); return sel,cost
q=64
policies={
 'uniform':      lambda pool,rng:(pool[:q],sum(tau[n] for n in pool[:q])),
 'odd h32 4x':   lambda pool,rng: odd(None,32,pool[:4*q],q,rng),
 'odd h16 4x':   lambda pool,rng: odd(None,16,pool[:4*q],q,rng),
 'odd h64 4x':   lambda pool,rng: odd(None,64,pool[:4*q],q,rng),
 'odd h32 8x':   lambda pool,rng: odd(None,32,pool[:8*q],q,rng),
 'odd h64 8x':   lambda pool,rng: odd(None,64,pool[:8*q],q,rng),
 'SH 8x 16/32/64': lambda pool,rng: halving(pool[:8*q],q,[(16,4*q),(32,2*q),(64,q)],rng),
 'SH 16x 16/32/64/96': lambda pool,rng: halving(pool[:16*q],q,[(16,8*q),(32,4*q),(64,2*q),(96,q)],rng),
 'SH 4x 32/64':  lambda pool,rng: halving(pool[:4*q],q,[(32,2*q),(64,q)],rng),
}
for lo in sorted(set(k[0] for k in rows)):
    strata=[k for k in rows if k[0]==lo]
    rho0=sum(q*313/6250 for k in strata)/sum(q*st.mean(t for _,t in rows[k]) for k in strata)
    out=[]
    for name,pol in policies.items():
        H=T=0
        for seed in range(32):
            rng=random.Random(seed*7919+lo)
            for k in strata:
                pool=rng.sample([n for n,_ in rows[k]],16*q)
                sel,cost=pol(pool,rng); H+=sum(credit[n] for n in sel); T+=cost
        out.append(f'{name}={H/T/rho0:.3f}')
    print(lo,' '.join(out),flush=True)
