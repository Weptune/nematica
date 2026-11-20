# Study J: does the recipe hold on moving worms once it is given what it lacked? (registration)

**Status: DRAFT** (20 Nov 2026, 20:28 UTC; written before the emulator recipe, in any form, was run on the copper set)

**Why.** The recipe that cannot be told from held-still, stimulated worms (README "A worm emulator") fails on
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

**Development (exploratory, Atanas worms, all three pools seen before; `results/journey_dev`, seed 0).**
Activity tests passed, of 6 (a test passes when inside in at least 2 of 3 pools):

| recipe | passed | fails |
|---|---|---|
| frozen recipe (`slow6d_indivslow1_hp_memfix_diag_hsd1`) | 1 | all but reversal-bout timing |
| plain copy fitted to rest (`var3_spontaneous`) | 3 | distribution, correlation (too typical), dimension |
| coupling restored (`slow6d_indivslow1_hp_memfix_hsd1`, from 8 Nov) | 4 | distribution, timescale |
| **both changes (`slow6d_indivslow1_hp_memfix_hsd1_gcop`)** | 4 | timescale, reversal-bout timing |
| both, no individual slow part (`slow6d_hp_memfix_gcop`) | 4 | dimension, reversal-bout timing |
| both, individual slow part with less spread (`..._hsd0.5_gcop`) | 5 | timescale |
| three more variants (weaker individual slow part, no spread) | 3 to 4 | |

With `gcop` the distribution test is inside in all three pools in every variant. Timescale and dimension
trade off against each other through the individual slow part, and reversal-bout timing flips on a single
pool. The variant that reached 5 did so on one such flip. **The recipe carried forward is the one with
exactly the two named changes and nothing else retuned**, not the best scorer: R1 below.

**Data for the test.** The copper set (Baskoylu et al. 2026, Dryad): 27 freely moving worms, 1600 frames of
0.6 s, 77 to 112 named neurons each, AVA in all. Same lab and pipeline as the Atanas worms. Split
`configs/splits/copper2026_cv3.yaml` (three pools of 9, written earlier for other studies). New adapter
`nematica/data/copper_pp.py`, a copy of the Atanas one.

**What has been seen.** The copper worms were used for The Face (per-worm linear models) and other benchmark
runs, so their activity statistics are not unknown to the project. No emulator-family model has been run on
them, except that the plain control was run once on one pool to check the adapter; its scores were not read.

**Models**, each refitted from scratch on the two training pools, five simulation seeds (0 to 4):
- **R0**, the frozen recipe: `hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1`.
- **R1**, with both changes: `hybrid_kernels_slow6d_indivslow1_hp_memfix_hsd1_gcop`.
- **C**, the control: `var3_spontaneous`.
- Descriptive, seeds 0 to 2: coupling only (`..._hp_memfix_hsd1`), shape only (`..._hp_memfix_diag_hsd1_gcop`).

**Scoring.** The six activity tests (distribution, timescale, correlation, dimension, lead-lag, reversal-bout
timing), each passing when inside in at least 2 of 3 pools; the pass mark is 5 of 6, as before.
`scripts/run_same_worms.py --copper --norm fluct`, table by `scripts/journey_table.py`.

**Claims.**
- **Informative:** the control misses the pass mark in at least 4 of 5 seeds. Otherwise all claims are
  undecided.
- **J1, the failure repeats:** R0 passes at most 4 of 6 in at least 4 of 5 seeds on these worms too.
- **J2, the two changes help:** R1 passes more tests than R0 in at least 4 of 5 seeds (same seed).
- **J3, the pass mark:** R1 passes at least 5 of 6 in at least 4 of 5 seeds. Development says this is
  unlikely (4 of 6 on the Atanas worms); it is registered because it is the question.

**Not testable here.** Whether movement or the lab is what breaks the frozen recipe: both moving sets come
from one lab, and the still worms from another.

**Also reported (seen data, not a test):** R1 on the Atanas worms with all five seeds.

**Limits written now.** `gcop` is for recordings without pokes: with pokes, the links learned from them would
be fitted to normal scores. So R1 is a recipe for resting activity only, and nothing here says it would
still pass the poke tests on the still worms. One lab; 9 worms per pool.
