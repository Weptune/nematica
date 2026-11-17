import json, numpy as np, collections
from scipy.stats import spearmanr
rows=[json.loads(l) for l in open('/tmp/s7/c1.jsonl')]
out={}
for inst in ("median","fastest","slowest","noisiest"):
    for sweep,ms in (("share",("M1_lag1","M1","M2_lag1")),("ratio",("M2_lag1","M2_int","M1_lag1"))):
        rr=[r for r in rows if r['inst']==inst and r['sweep']==sweep]
        lv=sorted({r['level'] for r in rr})
        for m in ms:
            x=[r['level'] for r in rr]; y=[r[m] for r in rr]
            rho=spearmanr(x,y,nan_policy='omit')[0]
            means=[float(np.nanmean([r[m] for r in rr if r['level']==l])) for l in lv]
            out[f"{inst}|{sweep}|{m}"]={"rho":round(float(rho),3),"means":[round(v,3) for v in means],"n":len(rr)}
            print(f"{inst:9s} {sweep:6s} {m:8s} rho {rho:.2f} means {np.round(means,2)} n={len(rr)}")
json.dump(out,open('/tmp/s7/c1_summary.json','w'),indent=1)
