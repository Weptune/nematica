#!/bin/bash
# Amendment 2: five simulation seeds, both splits, minimal and frozen models. One fold per call.
f=$1
M=hybrid_kernels_slow6d_indivslow1_hp_mem_diag
F=hybrid_kernels_indivshock_innov6_slow6d_indivslow1_hp_mem
run() { python scripts/run_same_worms.py --data data/raw/randi2023_wt_npz --folds configs/splits/$1 --norm fluct --pci --cache $2 --out /tmp/emu_rob --models $3 --seed-offset $4 --fold $f; }
for s in 0 1 2 3 4; do
  run pumpprobe_cv3.yaml results/emulator_select $M $s
  run pumpprobe_cv3_blocks1.yaml results/emulator_confirm $M $s
done
for s in 2 3 4; do run pumpprobe_cv3.yaml results/emulator_select $F $s; done
for s in 1 2 3 4; do run pumpprobe_cv3_blocks1.yaml results/emulator_confirm $F $s; done
