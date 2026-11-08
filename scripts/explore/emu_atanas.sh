#!/bin/bash
# Test T: the frozen recipe and the control on Atanas 2023 freely moving worms (rest only), five seeds.
f=$1
for s in 0 1 2 3 4; do
  python scripts/run_same_worms.py --data data/raw/atanas2023_wwweb --atanas --folds configs/splits/atanas2023_cv3.yaml --norm fluct --cache results/emulator_atanas --out /tmp/emu_a --models hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1,var3_spontaneous --seed-offset $s --fold $f
done
