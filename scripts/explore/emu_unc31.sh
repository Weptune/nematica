#!/bin/bash
# Test U: the frozen recipe and two controls on unc-31 worms, five seeds. One fold per call.
f=$1
M=hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1,var3_spontaneous,hybrid_kernels
for s in 0 1 2 3 4; do
  python scripts/run_same_worms.py --data data/raw/randi2023_unc31_npz --folds configs/splits/unc31_cv3.yaml --norm fluct --pci --cache results/emulator_unc31 --out /tmp/emu_u --models $M --seed-offset $s --fold $f
done
