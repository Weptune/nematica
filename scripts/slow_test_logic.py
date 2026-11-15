"""Synthetic check of the tests stage logic (SLOW_LOG, "Synthetic check of the tests stage"): known gaps
must give known verdicts. Writes only the git-ignored *_dry files."""
import sys, json, numpy as np; sys.path.insert(0,'/home/claude/nematica/scripts')
import slow_run as S
rng=np.random.default_rng(0)
mice={}
for i in range(58):
    m1=float(rng.normal(0.5,0.1)); m2=float(np.exp(rng.normal(1.0,0.3)))
    sp=lambda: {"M1":m1+rng.normal(0,0.03),"M2":m2*np.exp(rng.normal(0,0.1)),"no_shared":False,"no_locked":False,"int_ceiling":False}
    mice[f"m{i}"]=dict(id=f"m{i}",rank=i,M1=m1,M2=m2,no_shared=False,no_locked=False,int_ceiling=False,ti=m2*3,tl=3.0,split={"odd":sp(),"even":sp()})
ais=[]
def add(fam,run,mid,m1,m2,**kw): ais.append(dict(family=fam,run=run,id=mid,M1=m1,M2=m2,no_shared=False,no_locked=False,int_ceiling=False,reached=True,**kw))
for mid,m in mice.items():
    inst=m["rank"]%3
    add("A2",f"i{inst}",mid,m["M1"]-0.3,m["M2"]/3)                         # clear gap on both
    add("A3",f"i{inst}",mid,m["M1"]+0.3,m["M2"]*3)                         # AI above: refuted
    for gain,dm in zip(S.GAINS,np.linspace(-0.4,0.4,len(S.GAINS))):       # grid spans the mouse: d = 0
        add("A1",f"i{inst}-g0-gain{gain}",mid,m["M1"]+dm,m["M2"]*np.exp(dm))
    add("A5",f"i{inst}",mid,0.01,np.nan)                                   # no internal part
    for share in S.SLOW_SHARES:                                            # only share 0.2 tau 1.0 matches
        for tau in S.SLOW_TAUS_S:
            off=abs(share-0.2)+abs(tau-1.0)
            add("A1-slow",f"i{inst}-g0-share{share}-tau{tau}",mid,m["M1"]-off*0.5+rng.normal(0,0.02),m["M2"]*np.exp(-off))
        add("A1-fast",f"i{inst}-g0-share{share}",mid,m["M1"]-0.2+share*0.2,m["M2"]/4)   # never matches M2
    for nz in (0.2,0.4,0.8,1.6):
        add("A1-noise",f"i{inst}-g0-noise{nz}",mid,m["M1"]-0.3+nz*0.1,m["M2"]/3)
    add("A6",f"pythia-14m-seed1-i{inst}",mid,0.02,np.nan); add("A6",f"pythia-1b-i{inst}",mid,m["M1"]-0.1,m["M2"])
    if m["rank"]>=32:
        m["shuffled"]={"M1":m["M1"],"M2":m["M2"]*2.5,"tl":1.2,"ti":m["M2"]*3*1.05,"no_shared":False,"no_locked":False}
for name,rows in (("mice_dry.jsonl",list(mice.values())),("ais_dry.jsonl",ais)):
    with open(S.OUT/name,"w") as f:
        for r in rows: f.write(json.dumps(r)+"\n")
S.stage_tests(dry=True)
d=json.load(open(S.OUT/"tests_dry.json"))
for fam in ("A1","A2","A3","A5"):
    print(fam,{m:(d["H1"][fam][m].get("verdict"),round(d["H1"][fam][m].get("median_d_ruler",np.nan),2) if d["H1"][fam][m].get("median_d_ruler") is not None else None) for m in ("M1","M2")})
print("C3",d["C3"]); print("H2",{k:(v.get("chosen"),v.get("equivalent_both")) if isinstance(v,dict) else v for k,v in d["H2"].items()}); print("H3",d["H3"]); print("shuffled",d.get("validity_shuffled"))
