"""Continuous view behind the verdicts: for each model and level, the excess distance to real worms,
(model-to-real median minus real-to-real median) / real-to-real median, averaged over pools and seeds.
0 = as close to real worms as real worms are to each other; > 0 too different; < 0 too typical."""
import glob, re, sys, pandas as pd, numpy as np
LEV = ['L1.distribution', 'L1.timescale', 'L2.correlation', 'L2.dimension', 'L4.leadlag', 'L4.dwell', 'C1.pattern', 'C2.magnitude', 'P2.spread']
MODELS = [("VAR(3) from rest", "var3_spontaneous", "results/same_worms_pci"),
          ("first hybrid (rest + causal links)", "hybrid_kernels", "results/same_worms_pci"),
          ("previous best poke model", "hybrid_kernels_regimes_obsfit", "results/same_worms_pci"),
          ("emulator, buggy readout", "hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1", "results/emulator_select"),
          ("emulator, corrected readout", "hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1", "results/emulator_select")]
rows = []
for label, spec, cache in MODELS:
    fs = [f for f in glob.glob(f"{cache}/fluct_f[012]_{spec}*.csv") if re.fullmatch(rf".*_f\d_{re.escape(spec)}(_s\d)?\.csv", f)]
    if not fs:
        continue
    d = pd.concat([pd.read_csv(f) for f in fs])
    r = {"model": label, "runs": len(fs)}
    for L in LEV:
        x = d[d.metric == L]
        r[L.split(".")[1][:7]] = np.round(np.mean((x.system_median - x.bio_median) / x.bio_median), 3)
    rows.append(r)
t = pd.DataFrame(rows); pd.set_option("display.width", 250)
print("cv3 split; excess distance (0 = like real worms)"); print(t.to_string(index=False))
