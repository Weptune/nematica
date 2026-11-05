#!/bin/bash
# Lab H amendment: smallest hold (16, 30, 60 frames) at which individuals agree >= 0.07 in pool 0,
# judged on another_individual alone; then the full copies with that hold.
# Usage: scripts/lab_h_calibrate.sh TASK TRAINED(1|0)
cd "$(dirname "$0")/.."
task=$1; tr=$2; tag=$([ "$tr" = 1 ] && echo trained || echo init)
chosen=""
for h in 16 30 60; do
  out=docs/figures/ann_trained_calib_${task}_${tag}_h${h}.csv
  [ -f "$out" ] || NEMATICA_TASK=$task NEMATICA_TRAINED=$tr NEMATICA_SIGMA=0.3 NEMATICA_LEAD=230 NEMATICA_KICK_FRAMES=$h OMP_NUM_THREADS=1 \
    python3 -W ignore scripts/run_ann_trained.py ruler --n 113 --folds 0 --copies another_individual --out $out
  a=$(python3 -c "import csv;print([r for r in csv.DictReader(open('$out'))][0]['real_agreement'])")
  echo "$task $tag hold $h: individuals agree $a"
  if python3 -c "import sys;sys.exit(0 if float('$a')>=0.07 else 1)"; then chosen=$h; break; fi
done
if [ -z "$chosen" ]; then echo "$task $tag: unusable (no hold reaches 0.07)"; exit 0; fi
echo "$task $tag: chosen hold $chosen"
out=docs/figures/ann_trained_${task}_${tag}_hold${chosen}_fold0.csv
[ -f "$out" ] || NEMATICA_TASK=$task NEMATICA_TRAINED=$tr NEMATICA_SIGMA=0.3 NEMATICA_LEAD=230 NEMATICA_KICK_FRAMES=$chosen OMP_NUM_THREADS=1 \
  python3 -W ignore scripts/run_ann_trained.py ruler --n 113 --folds 0 --out $out
echo "$task $tag: done"
