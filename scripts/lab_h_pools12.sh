#!/bin/bash
# Lab H: pools 1 and 2 with each network's calibrated hold (pool 0 results in *_fold0.csv)
cd "$(dirname "$0")/.."
run() { task=$1; tr=$2; tag=$3; h=$4
  out=docs/figures/ann_trained_${task}_${tag}_hold${h}_folds12.csv
  [ -f "$out" ] || NEMATICA_TASK=$task NEMATICA_TRAINED=$tr NEMATICA_SIGMA=0.3 NEMATICA_LEAD=230 NEMATICA_KICK_FRAMES=$h OMP_NUM_THREADS=1 \
    python3 -W ignore scripts/run_ann_trained.py ruler --n 113 --folds 1,2 --out $out
  echo "$task $tag pools 1,2 done"; }
case $1 in
  A) run cdi 1 trained 30; run cdi 0 init 16;;
  B) run flipflop 1 trained 30; run flipflop 0 init 16;;
esac
