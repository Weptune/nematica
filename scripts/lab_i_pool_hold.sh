#!/bin/bash
# Lab I, pooling condition: pools 1 and 2 were unusable (individuals agree < 0.05), so, as
# pre-registered, the hold is lengthened (16, 30, 60 frames) until individuals agree >= 0.07 in pool 0,
# judged on another_individual alone; then pools 0 to 2 with that hold.
cd "$(dirname "$0")/.."
chosen=""
for h in 16 30 60; do
  out=docs/figures/ann_imperfect_calib_pool_h${h}.csv
  [ -f "$out" ] || NEMATICA_POOL=1 NEMATICA_KICK_FRAMES=$h NEMATICA_LEAD=230 OMP_NUM_THREADS=1 python3 -W ignore scripts/run_ann_imperfect.py --n 113 --folds 0 --copies another_individual --out $out
  a=$(python3 -c "import csv;print([r for r in csv.DictReader(open('$out'))][0]['real_agreement'])")
  echo "pool hold $h: individuals agree $a"
  if python3 -c "import sys;sys.exit(0 if float('$a')>=0.07 else 1)"; then chosen=$h; break; fi
done
[ -z "$chosen" ] && { echo "pool: unusable at every hold"; exit 0; }
NEMATICA_KICK_FRAMES=$chosen scripts/lab_i_run.sh pool_hold$chosen 0,1,2 NEMATICA_POOL=1 NEMATICA_KICK_FRAMES=$chosen
echo "pool chosen hold $chosen done"
