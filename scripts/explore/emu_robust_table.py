"""Amendment 2 summary: per model, split and seed, rest/poke counts and pass; then passes out of 5."""
import glob, re, pandas as pd
REST = ['L1.distribution', 'L1.timescale', 'L2.correlation', 'L2.dimension', 'L4.leadlag', 'L4.dwell']
POKE = ['C1.pattern', 'C2.magnitude', 'P2.spread']
MODELS = {"minimal": "hybrid_kernels_slow6d_indivslow1_hp_mem_diag", "minimal+hsd1": "hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1", "frozen": "hybrid_kernels_indivshock_innov6_slow6d_indivslow1_hp_mem"}
out = []
for split, cache in (("cv3 (selection)", "results/emulator_select"), ("blocks1 (confirmation)", "results/emulator_confirm")):
    for label, m in MODELS.items():
        for s in range(5):
            sfx = f"_s{s}" if s else ""
            fs = [f"{cache}/fluct_f{f}_{m}{sfx}.csv" for f in range(3)]
            try:
                d = pd.concat([pd.read_csv(f) for f in fs])
            except FileNotFoundError:
                continue
            v = {k: "".join(d[d.metric == k].sort_values("fold").verdict.map(lambda x: {"inside": "I", "outside": "O", "too typical": "T"}.get(x, "?"))) for k in REST + POKE}
            rest = sum(x.count("I") >= 2 for x in (v[k] for k in REST))
            poke = sum(x.count("I") >= 2 for x in (v[k] for k in POKE))
            out.append({"split": split, "model": label, "seed": s, **{k.split(".")[1][:6]: v[k] for k in REST + POKE}, "rest": rest, "poke": poke, "pass": rest >= 5 and poke == 3, "full": rest == 6 and poke == 3})
t = pd.DataFrame(out)
pd.set_option("display.width", 250)
print(t.to_string(index=False))
print(t.groupby(["model", "split"])[["pass", "full"]].agg(["sum", "count"]))
