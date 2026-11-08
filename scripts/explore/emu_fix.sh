#!/bin/bash
# Re-run with the corrected member readout: unc-31 and Atanas first, then both atlas splits.
f=$1
R=hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1
for s in 0 1 2 3 4; do
  python scripts/run_same_worms.py --data data/raw/randi2023_unc31_npz --folds configs/splits/unc31_cv3.yaml --norm fluct --pci --cache results/emulator_unc31 --out /tmp/emu_u --models $R --seed-offset $s --fold $f
  python scripts/run_same_worms.py --data data/raw/atanas2023_wwweb --atanas --folds configs/splits/atanas2023_cv3.yaml --norm fluct --cache results/emulator_atanas --out /tmp/emu_a --models $R --seed-offset $s --fold $f
done
for s in 0 1 2 3 4; do
  python scripts/run_same_worms.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3.yaml --norm fluct --pci --cache results/emulator_select --out /tmp/emu_rob --models $R --seed-offset $s --fold $f
  python scripts/run_same_worms.py --data data/raw/randi2023_wt_npz --folds configs/splits/pumpprobe_cv3_blocks1.yaml --norm fluct --pci --cache results/emulator_confirm --out /tmp/emu_rob --models $R --seed-offset $s --fold $f
done
