import gzip, csv, sys, collections, statistics as st, math
B=sys.argv[1]
rows=collections.defaultdict(list)
with gzip.open(f'{B}/test/reference.csv.gz','rt') as f:
    for r in csv.DictReader(f): rows[(int(r['lower']),int(r['stratum']))].append((int(r['n']),int(r['stopping_time'])))
def pref(n,h):
    k=0;x=n
    for i in range(h):
        if x==1: break
        if x&1: x=3*x+1;k+=1
        else: x>>=1
    return k,x,i
c=1.5*2/math.log(4/3)
print('model constant C-steps per ln n =',round(c,3))
lowers=sorted(set(k[0] for k in rows))
for lo in lowers:
    allt=[t for k in rows if k[0]==lo for _,t in rows[k]]
    mid=lo+50000
    print(f'== {lo}: mean tau {st.mean(allt):.2f} sd {st.pstdev(allt):.2f}  model c*ln n {c*math.log(mid):.2f}')
    # quartile tie-fair density
    qd=[0.0]*4
    for k in rows:
        if k[0]!=lo: continue
        v=sorted(rows[k],key=lambda x:(-x[1],x[0]));ts=v[312][1];above=sum(1 for _,t in v if t>ts);tie=sum(1 for _,t in v if t==ts);tt=313-above
        for n,t in rows[k]:
            off=n-(lo+6250*k[1]);qd[min(3,off*4//6250)]+=(t>ts)+(t==ts)*tt/tie
    print('  tie-fair target share by within-stratum quartile:',[round(x/(313*16),3) for x in qd])
    for h in (16,32,64):
        xs=[];ys=[];resid=[]
        byk=collections.defaultdict(list)
        for k in rows:
            if k[0]!=lo: continue
            for n,t in rows[k]:
                kk,x,_=pref(n,h); xs.append(kk); ys.append(t); byk[kk].append(t)
        mx,my=st.mean(xs),st.mean(ys); sxy=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); sxx=sum((a-mx)**2 for a in xs); syy=sum((b-my)**2 for b in ys)
        slope=sxy/sxx; r2=sxy*sxy/(sxx*syy)
        print(f'  h={h}: slope dtau/dk {slope:.2f} (model c*ln6={c*math.log(6):.2f}) R^2 {r2:.3f}')
