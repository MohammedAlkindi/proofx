import gzip, json, csv, sys, collections, statistics as st
B = sys.argv[1]
ref = {}
strata = collections.defaultdict(list)
with gzip.open(B + '/test/reference.csv.gz', 'rt') as f:
    for r in csv.DictReader(f):
        n=int(r['n']); t=int(r['stopping_time']); key=(int(r['lower']),int(r['stratum']))
        ref[n]=(t,int(r['target']),key); strata[key].append((t,n))
thr={}; tieinfo={}
for key,v in strata.items():
    v.sort(key=lambda x:(-x[0],x[1])); ts=v[312][0]
    above=sum(1 for t,_ in v if t>ts); tie=sum(1 for t,_ in v if t==ts)
    thr[key]=(ts,above,tie,313-above)
tot_tie_targets=sum(x[3] for x in thr.values()); print('strata',len(thr),'targets that are boundary-tie members',tot_tie_targets,'of',313*len(thr))
print('mean tie-group size',st.mean(x[2] for x in thr.values()),'mean tie targets/stratum',st.mean(x[3] for x in thr.values()))
agg=collections.defaultdict(lambda: collections.defaultdict(list))
over=collections.defaultdict(list); sel={}
with gzip.open(B + '/test/runs.jsonl.gz','rt') as f:
    for line in f:
        r=json.loads(line)
        if r['budget']!=1024: continue
        hits=strict=frac=0; taus=[]
        for rec in r['selected']:
            n=rec[0]; t,tg,key=ref[n]; ts,above,tie,tt=thr[key]
            hits+=tg; strict+= t>ts; frac+= (t>ts) + (t==ts)*tt/tie; taus.append(t)
        m=(r['lower'],r['method'])
        agg[m]['hits'].append(hits); agg[m]['strict'].append(strict); agg[m]['frac'].append(frac); agg[m]['meantau'].append(st.mean(taus))
        agg[m]['charged'].append(r['charged_transitions'])
        sel[(r['lower'],r['seed'],r['method'])]=set(x[0] for x in r['selected'])
print(f"{'lower':>10} {'method':>12} {'hits':>8} {'strict>':>8} {'tieFrac':>8} {'meanTau':>8} {'charged':>9}")
for m in sorted(agg):
    a=agg[m]; print(f"{m[0]:>10} {m[1]:>12} {st.mean(a['hits']):8.2f} {st.mean(a['strict']):8.2f} {st.mean(a['frac']):8.2f} {st.mean(a['meantau']):8.2f} {st.mean(a['charged']):9.0f}")
for lo in sorted(set(k[0] for k in sel)):
    ov=[len(sel[(lo,s,'growth')]&sel[(lo,s,'odd_count')])/1024 for s in range(32) if (lo,s,'growth') in sel and (lo,s,'odd_count') in sel]
    print('overlap growth/odd',lo,st.mean(ov) if ov else None)
