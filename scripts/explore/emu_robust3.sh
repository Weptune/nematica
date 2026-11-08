#!/bin/bash
# Amendment 3: minimal model plus single-neuron slow participation, five seeds, both splits.
f=$1
M=hybrid_kernels_slow6d_indivslow1_hp_mem_diag_hsd1
run() { python scripts/run_same_worms.py --data data/raw/randi2023_wt_npz --folds configs/splits/$1 --norm fluct --pci --cache $2 --out /tmp/emu_rob --models $M --seed-offset $3 --fold $f; }
for s in 0 1 2 3 4; do
  run pumpprobe_cv3.yaml results/emulator_select $s
  run pumpprobe_cv3_blocks1.yaml results/emulator_confirm $s
done
