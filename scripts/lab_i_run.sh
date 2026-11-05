#!/bin/bash
# Lab I runs. Usage: scripts/lab_i_run.sh NAME FOLDS ENV...   e.g. lab_i_run.sh offtarget 0 NEMATICA_OFFTARGET=0.5
cd "$(dirname "$0")/.."
name=$1; folds=$2; shift 2
tag=$(echo $folds | tr -d ,)
out=docs/figures/ann_imperfect_${name}_folds${tag}.csv
[ -f "$out" ] || env "$@" NEMATICA_LEAD=230 OMP_NUM_THREADS=1 python3 -W ignore scripts/run_ann_imperfect.py --n 113 --folds $folds --out $out
echo "$name folds $folds done"
