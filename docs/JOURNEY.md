# Study J: does the recipe hold on moving worms once it is given what it lacked? (registration)

**Status: FROZEN** (20 Nov 2026, 20:51 UTC; written, reviewed and frozen before the emulator recipe, in any form, was run on the copper set)

**Why.** The recipe that passes this project's tests on held-still, stimulated worms (README "A worm emulator") fails on
freely moving worms from another lab: 1 of 6 activity tests on the 30 Atanas et al. worms, below a plain
copy fitted to rest (3 of 6) (README "Testing the emulator recipe on data it was not built on", test T). The
exploratory diagnosis of 8 Nov named two things the recipe lacked there: coupling between neuron types, and
skewed activity. This study gives it both and tests the result on moving worms the recipe has never met.

**Two changes, named in advance.**
- *Coupling between neuron types:* the fast part is a full matrix again (spec without `diag`).
- *Skewed activity:* new ingredient `gcop` (`nematica/systems/causal_models.py`, marked [J]). Every neuron's
  trace is replaced by its normal scores before anything is fitted, so the dynamics are learned on ranks.
  Each simulated worm then takes, class by class, the distribution shape of one training worm chosen at
  random (pooled shape where that worm lacks the class). The 8 Nov attempt mapped a model fitted to raw
  values onto one pooled shape; it made every worm's distribution alike and broke timescales.

**Development (exploratory, Atanas worms, all three pools seen before; seed 0).** Activity tests passed, of 6
(a test passes when inside in at least 2 of 3 pools). The table was regenerated after the review's order fix
(below; `results/journey_dev2`, `docs/figures/journey_journey_dev2.json`):

| recipe | passed | fails |
|---|---|---|
| frozen recipe (`slow6d_indivslow1_hp_memfix_diag_hsd1`) | 1 | all but reversal-bout timing |
| plain copy fitted to rest (`var3_spontaneous`) | 3 | distribution, correlation (too typical), dimension |
| coupling restored (`slow6d_indivslow1_hp_memfix_hsd1`, from 8 Nov) | 4 | distribution, timescale |
| shape only (`slow6d_indivslow1_hp_memfix_diag_hsd1_gcop`) | 1 | all but distribution |
| **both changes (`slow6d_indivslow1_hp_memfix_hsd1_gcop`)** | 4 | timescale, reversal-bout timing |
| both, no individual slow part (`slow6d_hp_memfix_gcop`) | 5 | dimension |
| both, individual slow part with less spread (`..._hsd0.5_gcop`) | 5 | timescale |

With `gcop` the distribution test is inside in all three pools in every variant. Timescale and dimension
trade off against each other through the individual slow part, and reversal-bout timing flips on a single
pool: the two variants that reach 5 do so on such a flip, and before the order fix the same seed gave 4 for
one of them. **The recipe carried forward is the one with exactly the two named changes and nothing else
retuned**, not the best scorer: R1 below. *(Table before the fix, `results/journey_dev`: frozen 1, control 3,
coupling 4, both 4, no individual slow part 4, less spread 5, three weaker variants 3 to 4.)*

**Data for the test.** The copper set (Baskoylu et al. 2026, Dryad): 27 freely moving worms, 1600 frames of
0.6 s (0.595 s in one worm), 77 to 116 named neurons each, AVA in all. Same lab and pipeline as the Atanas
worms. Split `configs/splits/copper2026_cv3.yaml` (three pools of 9, written earlier for other studies). New
adapter `nematica/data/copper_pp.py`, a copy of the Atanas one. *(Review:)* these worms crawl in an arena with
an aversive copper boundary and meet it during the recording (70 encounters in the 27 worms, by the
project's Level 6 definition). All frames are kept and no encounter is passed to any model, so the real
worms' activity includes responses to copper that the copies are never told about.

**What has been seen.** The copper worms were used for The Face (per-worm linear models) and other benchmark
runs, so their activity statistics are not unknown to the project. *(Review:)* linear models have been fitted
to them before: per-worm and pooled VARs for the benchmark, and a pooled class-level VAR in
`scripts/run_copper_vs_pokes.py`. No recipe of the emulator family (`hybrid_kernels`) has been run on them.
The plain control was run once on pool 0 at seed 0 to check the adapter; its scores were not read, and that
file is kept as that pool's control result.

**Models**, each refitted from scratch on the two training pools, five simulation seeds (0 to 4):
- **R0**, the frozen recipe: `hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1`.
- **R1**, with both changes: `hybrid_kernels_slow6d_indivslow1_hp_memfix_hsd1_gcop`.
- **C**, the control: `var3_spontaneous`.
- Descriptive, seeds 0 to 2: coupling only (`..._hp_memfix_hsd1`), shape only (`..._hp_memfix_diag_hsd1_gcop`).

**Scoring.** The six activity tests (distribution, timescale, correlation, dimension, lead-lag, reversal-bout
timing), each passing when inside in at least 2 of 3 pools; the pass mark is 5 of 6, as before. A test that
a pool's file lacks, or that the bench could not score, counts as not inside. The run, per pool `f` and seed
`s`:

    python3 -I scripts/run_same_worms.py --data data/raw/doi_10_5061_dryad_w9ghx3g4v__v20260415 --copper \
      --folds configs/splits/copper2026_cv3.yaml --norm fluct --cache results/journey_copper --out /tmp/emu_c \
      --models <specs> --seed-offset s --fold f

(`--out` is given because the default would overwrite `docs/figures/same_worms_fluct.csv`.) The table and
the claims come from `python3 -I scripts/journey_table.py results/journey_copper --claims`, which stops if any
registered model, seed or pool is missing. **One run: nothing is rerun, whatever it shows.** After the order
fix a seed fixes the result (two separate processes gave identical files).

**Claims.**
- **Informative:** the control misses the pass mark in at least 4 of 5 seeds. Otherwise all claims are
  undecided.
- **J1, the failure repeats:** R0 passes at most 4 of 6 in at least 4 of 5 seeds on these worms too.
- **J2, the two changes help:** *(changed by the review)* on the five tests other than distribution, R1 passes
  more than R0 in at least 4 of 5 seeds (same seed). The distribution test is left out because `gcop` passes
  it by construction: each simulated worm's class shapes are copied from a real training worm.
- **J3, the pass mark:** R1 passes at least 5 of 6 in at least 4 of 5 seeds. Since one of the six is passed by
  construction, this asks in effect for 4 of the other 5. Development says it is unlikely (4 of 6 on the
  Atanas worms at seed 0; variants a single flip away reach 5); it is registered because it is the question.

**Not testable here.** Whether movement or the lab is what breaks the frozen recipe: both moving sets come
from one lab, and the still worms from another.

**Also reported (seen data, not a test):** R1 on the Atanas worms with all five seeds.

**Limits written now.** `gcop` is for recordings without pokes: with pokes, the links learned from them would
be fitted to normal scores. So R1 is a recipe for resting activity only, and nothing here says it would
still pass the poke tests on the still worms. One lab; 9 worms per pool.
`gcop` learns on each neuron's own normal scores but hands back shapes per neuron class, so for classes with
several members the two steps are not exact inverses (reviewer's check on the Atanas worms: rank agreement
median 0.99, minimum 0.78), and single neurons stay less skewed than real ones (0.44 against 1.08).

## Review before the freeze (independent agent, 20 Nov 2026; it ran nothing on the copper set)

1. **Blocking, accepted.** `_simulate_members` drew each class's member noise in the order of a Python set of
   strings, which changes from one process to the next, so a seed did not fix a result: three identical runs
   of R1 at seed 0 on the Atanas worms differed, and reversal-bout timing flipped in one pool. It touches
   every recipe with `memfix` (R0, R1), not the control. **Fixed:** the loop is sorted (`causal_models.py`,
   marked [J]). This changes the order of random draws in the frozen recipe and nothing else. Checked: two
   separate processes now give identical files. The development table above was regenerated; the frozen
   recipe's earlier published numbers (README "A worm emulator") were each one draw from this spread and are
   not regenerated here.
2. **Accepted.** J2 is now judged on the five tests other than distribution, and J3 says that one test is
   passed by construction.
3. **Accepted.** The copper boundary, and the linear models already fitted to these worms, are stated.
4. **Accepted.** `scripts/journey_table.py` rewritten: it stops if a registered model, seed or pool is
   missing, counts a missing or unscored test as not inside, and evaluates the claims itself.
5. **Accepted.** What `gcop` does and does not restore is stated under the limits. The reviewer found no leak
   of test worms into the shapes.
6. No change needed: ties, missing values and constant traces behave in `normal_scores`.
7. **Accepted.** Named neurons are 77 to 116, and one worm's frame is 0.595 s.
8. **Accepted.** The full command is registered; "cannot be told from" replaced by what was measured.
