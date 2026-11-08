"""Per model and seed: verdict letters per level, rest and poke counts, rule pass. Usage:
seed_table.py <cache> <model,model,...> [rest-only]"""
import sys, glob, pandas as pd
cache, models = sys.argv[1], sys.argv[2].split(",")
rest_only = len(sys.argv) > 3
REST = ['L1.distribution', 'L1.timescale', 'L2.correlation', 'L2.dimension', 'L4.leadlag', 'L4.dwell']
POKE = [] if rest_only else ['C1.pattern', 'C2.magnitude', 'P2.spread']
AB = {"inside": "I", "outside": "O", "too typical": "T"}
rows = []
for m in models:
    for s in range(5):
        sfx = f"_s{s}" if s else ""
        fs = sorted(glob.glob(f"{cache}/*_f[0-9]_{m}{sfx}.csv"))
        if not fs:
            continue
        d = pd.concat([pd.read_csv(f) for f in fs])
        v = {k: "".join(d[d.metric == k].sort_values("fold").verdict.map(lambda x: AB.get(x, "-"))) for k in REST + POKE}
        ok = lambda x: x.count("I") >= 2 if len(x) == 3 else False
        rest = sum(ok(v[k]) for k in REST); poke = sum(ok(v[k]) for k in POKE)
        rows.append({"model": m[:40], "seed": s, "folds": len(fs), **{k.split(".")[1][:6]: v[k] for k in REST + POKE},
                     "rest": rest, "poke": poke, "pass": rest >= 5 and poke == len(POKE)})
t = pd.DataFrame(rows); pd.set_option("display.width", 250)
print(t.to_string(index=False))
print(t[t.folds == 3].groupby("model")["pass"].agg(["sum", "count"]))
