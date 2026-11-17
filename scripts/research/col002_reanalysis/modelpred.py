# Parameter-free stochastic-model prediction of PX-COL-002 odd-count enrichment.
# Model: each ordinary step from an odd value is 3x+1 (then forced even); parity of each new value
# after a halving is a fair coin. Total stopping time modeled as h + R(log x_h), where R is the
# hitting time of log x <= 0 in the random walk. We compare: model top-5% enrichment when selecting
# top-q of 4q by k_32 with random tiebreak, vs observed (tie-fair) enrichment from the data.
import math, random, statistics as st, sys
rng = random.Random(1)
def walk(L, step0_odd):
    # L = ln x ; returns steps to reach x<=1 under model, starting with parity step0_odd
    t=0; odd=step0_odd
    while L > 0.0:
        if odd:
            L += math.log(3) + math.log1p(1/(3*math.exp(L)) if L<50 else 0.0); t+=1; odd=False  # 3x+1 is even
        else:
            L -= math.log(2); t+=1; odd = rng.random()<0.5
    return t
def prefix(L0, h):
    L=L0; k=0; odd = rng.random()<0.5; t=0
    while t<h:
        if odd: L+=math.log(3); k+=1; odd=False
        else: L-=math.log(2); odd = rng.random()<0.5
        t+=1
    return k, L, odd
for lo in (2097152, 33554432, 536870912):
    L0 = math.log(lo+50000)
    N=6250*8
    pop=[]
    for _ in range(N):
        k,L,odd=prefix(L0,32)
        tau = 32 + walk(L,odd)
        pop.append((k,tau))
    taus=sorted((t for _,t in pop), reverse=True)
    K=int(0.05008*N); ts=taus[K-1]; above=sum(t>ts for t in taus); tie=sum(t==ts for t in taus); w=(K-above)/tie
    credit=lambda t: (t>ts)+(t==ts)*w
    # selection: pools of 4q=256 from population, take top 64 by k (random tiebreak)
    hits=[]; reps=400
    for _ in range(reps):
        pool=rng.sample(pop,256); pool.sort(key=lambda x:(-x[0],rng.random()))
        hits.append(sum(credit(t) for _,t in pool[:64]))
    enrich = st.mean(hits)/(64*K/N)
    mt=st.mean(t for _,t in pop); sd=st.pstdev(t for _,t in pop)
    xs=[k for k,_ in pop]; ys=[t for _,t in pop]; mx,my=st.mean(xs),st.mean(ys)
    slope=sum((a-mx)*(b-my) for a,b in zip(xs,ys))/sum((a-mx)**2 for a in xs)
    r2=slope**2*st.pvariance(xs)/st.pvariance(ys)
    print(f'{lo}: model mean tau {mt:.1f} sd {sd:.1f} slope {slope:.2f} R2 {r2:.3f} odd-count top-64/256 enrichment {enrich:.3f}')
