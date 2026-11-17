import random, statistics as st, sys
def tau(n):
    t=0
    while n!=1:
        n = n>>1 if n%2==0 else 3*n+1; t+=1
    return t
rng=random.Random(20261116)
W=6250; S=16
res=[]
for trial in range(int(sys.argv[1])):
    e=rng.choice([21,25,29,33]); lo=rng.randrange(2**e, 2**(e+1)-W*S)
    q=[0.0]*4; means=[]
    for s in range(S):
        base=lo+W*s; v=[(tau(base+j),j) for j in range(W)]
        ts=sorted((t for t,_ in v),reverse=True)[312]; above=sum(t>ts for t,_ in v); tie=sum(t==ts for t,_ in v); tt=313-above
        for t,j in v: q[min(3,j*4//W)]+=(t>ts)+(t==ts)*tt/tie
        means.append(st.mean(t for t,_ in v))
    sh=[round(x/(313*S),3) for x in q]; res.append(sh[0])
    print(e, lo, 'quartile shares', sh, 'window mean tau', round(st.mean(means),1), 'stratum-mean sd', round(st.pstdev(means),1), flush=True)
print('Q1 share across windows: mean',round(st.mean(res),3),'sd',round(st.pstdev(res),3))
