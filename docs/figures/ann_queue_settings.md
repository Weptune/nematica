# Settings of the queued lab checks (scripts/lab_queue.py)

All: `scripts/run_ann_calcium.py --n 113`, kick 6, first poke at frame 230, copies another_individual,var3_spontaneous,stitch3_hp,hybrid_kernels. Unlisted variables at defaults (BRAIN_SEED 0, GATED 0, KICK_FRAMES 8, SUBSTEPS 1, CALCIUM 0).

| File | Environment | Arguments |
|---|---|---|
| ann_queue_silent_seed1_fold0.csv | BRAIN_SEED=1 GATED=1.5 KICK_FRAMES=4 | --share 0.05 --folds 0 |
| ann_queue_baseline_seed1_fold0.csv | BRAIN_SEED=1 KICK_FRAMES=4 | --share 0.05 --folds 0 |
| ann_queue_silent_seed2_fold0.csv | BRAIN_SEED=2 GATED=1.5 KICK_FRAMES=4 | --share 0.05 --folds 0 |
| ann_queue_baseline_seed2_fold0.csv | BRAIN_SEED=2 KICK_FRAMES=4 | --share 0.05 --folds 0 |
| ann_queue_calcium3.0_fold0.csv | SUBSTEPS=5 CALCIUM=3.0 | --share 0.05 --folds 0 |
| ann_queue_calcium1.5_fold1.csv | SUBSTEPS=5 CALCIUM=1.5 | --share 0.05 --folds 1 |
| ann_queue_calcium1.5_fold2.csv | SUBSTEPS=5 CALCIUM=1.5 | --share 0.05 --folds 2 |
