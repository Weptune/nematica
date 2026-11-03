# Settings behind the lab E to G outputs (3 Nov 2026)

All runs: `scripts/run_ann_calcium.py --n 113` (113 individuals, sigma 0.3), atlas-format
recordings with the first poke at frame 230 (`NEMATICA_LEAD=230`), kick 6, the unchanged ruler.
Environment variables not listed are at their defaults (SUBSTEPS 1, CALCIUM 0, GATED 0,
LOWRANK 0, KICK_FRAMES 8).

| File | Folds | --share | Environment |
|---|---|---|---|
| ann_calcium_fold0.csv | 0 | 0.05 | SUBSTEPS=5 CALCIUM=1.5 |
| (direct-readout control, stopped after pool 0: old watching copy 0.60) | 0 | 0.05 | SUBSTEPS=5 CALCIUM=0 |
| ann_lowdim_drives.csv | 0,1,2 | 0.75 | KICK_FRAMES=30 |
| ann_lowdim_internal.csv | 0,1,2 | 0.05 | LOWRANK=1.7 KICK_FRAMES=30 |
| ann_gated_g0.5_fold0.csv | 0 | 0.05 | GATED=0.5 |
| ann_gated_g1.5_fold0.csv | 0 | 0.05 | GATED=1.5 |
| ann_silent_links.csv | 0,1,2 | 0.05 | GATED=1.5 KICK_FRAMES=4 |
| ann_silent_links_g1.5_f2_fold0.csv | 0 | 0.05 | GATED=1.5 KICK_FRAMES=2 |
| ann_control_shortpoke_fold0.csv | 0 | 0.05 | KICK_FRAMES=4 |
| ann_silent_links_on_drives_fold0.csv | 0 | 0.75 | GATED=1.5 KICK_FRAMES=16 |
| ann_silent_links_on_internal_fold0.csv | 0 | 0.05 | GATED=1.5 LOWRANK=1.7 KICK_FRAMES=16 |

Calibration runs (individual agreement only, pool 0): drives brain with KICK_FRAMES 16 / 30 / 60
gave 0.057 / 0.095 / 0.063; internal brain with KICK_FRAMES 30 gave 0.088.
True-K truth columns are not computed in these runs (left empty).
