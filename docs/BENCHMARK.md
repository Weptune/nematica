# The NEMATICA worm benchmark

**Can anyone tell your brain model from a real worm?** This benchmark tests a whole-brain model of
*C. elegans* the way real worms test each other. The model simulates held-out real worms, at rest and
while single neurons are switched on with light, exactly as in the experiments. Its simulated worms are
then compared with the real ones on eleven statistics. Each statistic is judged against how much real
worms differ from each other, not against a fixed threshold.

The data is the signal propagation atlas of Randi et al. (2023, *Nature*): 113 wild-type worms, about
37 minutes each at 2 frames per second. In every worm, a single neuron is switched on optogenetically
every 30 seconds or so, while the whole head is imaged.

## What makes it different

- **Calibrated against real variation.** A statistic is *inside* when the model's worms are no further
  from held-out real worms than real worms are from each other. A bootstrap over worms decides this.
- **Too typical fails too.** A model whose worms are all alike, an average worm, sits closer to every
  real worm than real worms sit to each other. The benchmark flags that as *too typical*.
- **Rest and perturbation together.** In this project, looking right at rest did not predict being
  right when poked: rank correlation -0.12 across 30 models. So both halves are scored, and the poke half
  can only be passed by learning cause and effect.
- **A registered pass rule, applied seed by seed.** The rule was fixed before the models it is reported
  for were scored. Each noise seed is judged on its own.
- **Effect sizes, not just verdicts.** Every level gets an excess distance with an interval, so a pass
  that sits on a knife edge looks like one.
- **Neuron-level readout.** Models answer one row per real neuron, and are read out exactly as real
  neurons are. Class-level readouts were found to inflate simulated echoes.
- **Honest about its limits** (see the end of this document).

## Quick start

```bash
pip install -e .                        # Python 3.11+, numpy, scipy, pyyaml
# data: download exported_data.tar.gz from https://osf.io/e2syt/ (Randi et al. 2023), unpack, then
python scripts/convert_pumpprobe.py --src path/to/exported_data --out data/raw/randi2023_wt_npz
python -m nematica score examples/copies/linear_rest.py:LinearRest --quick       # a first look, minutes
python -m nematica score path/to/my_copy.py:MyCopy --seeds 3                      # the full test
```

The full test writes `results/scores/<name>.json` and `results/scores/<name>.html`. It prints the
answer in the terminal:

```
Split cv3 (3 held-out pools, 3 noise seeds): passes at rest in 3/3, when poked in 3/3, both in 3/3
  level                    verdicts by seed       excess distance (median, range over pools)
  at rest
    activity distribution  III III III            +0.01 (-0.00 to +0.03); further than real in 6/9
    ...
```

## Write a copy (Python)

```python
import numpy as np
from nematica.score import BrainCopy

class MyCopy(BrainCopy):
    name = "my-copy"

    def fit(self, worms):
        # training recordings: uid, x (neurons x frames, NaN where untracked), names, classes, stims, dt
        ...

    def run(self, worm, rng):
        # worm.names: the real worm's neurons ("" where unidentified); worm.n_frames; worm.dt (0.5 s)
        # worm.pokes: (neuron, index, frame, drive). drive = that neuron's own measured response,
        # in SD units from its pre-poke baseline: hold the poked neuron to it, or use it as input.
        x = np.full((len(worm.names), worm.n_frames), np.nan)   # NaN rows: neurons you do not model
        ...
        return x
```

For each fold, the copy is fitted on the training worms only. It then runs every held-out worm of that
fold, with that worm's own neurons and pokes. `fit` is called once per fold. With `--seeds 3`, each
held-out worm is simulated three times with fresh noise (`rng`).

## Other languages

```bash
python -m nematica export --out kit/                 # fold lists + held-out templates (local only)
# fit and simulate in Julia, MATLAB, R, C++ ... then save
#   sims/<split>/fold<k>/seed<s>/<uid>.npz   with one array x: (len(names), n_frames)
python -m nematica score-files sims/ --name my-copy
```

`kit/README.txt` gives the file formats. The converted recordings (`pumpprobe_<uid>.npz`: `x`, `ids`,
`stim_cell`, `stim_frame`, `t`) and the templates are plain npz files. A missing worm or a wrong shape
is an error, not a silent skip.

## The levels and the rule

| level | what it compares between two worms |
|---|---|
| activity distribution | how each neuron class's activity values are distributed |
| timescale | how long each class's activity takes to forget itself |
| correlation pattern | which classes rise and fall together |
| dimensionality | how many independent patterns the activity spreads over |
| lead and lag | which classes lead and which follow, at about 2 and 6 s |
| reversal-bout timing | how long the reversal command neuron AVA stays high |
| echo pattern | which classes answer a poke of which, and with what sign |
| echo size | how strongly neurons answer pokes |
| echo spread | how much of the brain a single poke significantly moves |
| echo time course *(reported, not in the rule)* | time course of the strongest answers |
| echo complexity *(reported, not in the rule)* | compressibility of the significant answers |

There are two frozen splits of the 113 worms, each into 3 held-out pools of about 37 worms.

**The rule.**
- A level passes when it is inside in at least 2 of the 3 pools.
- A copy passes **at rest** when at least 5 of the 6 activity levels pass.
- It passes **when poked** when echo pattern, echo size and echo spread all pass.

**Excess distance** is (median model-to-real distance minus median real-to-real distance) divided by
the median real-to-real distance. At 0 the model's worms are as different from real worms as real
worms are from each other; at +0.5 they are 50% further; a negative value means too typical.

## Reference results

REFERENCE_TABLE

## Limits (read before claiming anything)

- **One dataset.** Both splits rearrange the same 113 worms. Passing both splits under several noise
  seeds shows robustness, not confirmation on new animals.
- **Inside is not agreement.** With 3 pools per split, small consistent differences can pass. Look at
  the excess distances: a level whose dots sit on one side of zero in every pool is off, even when it
  passes.
- **Lead and lag has little power.** Real worms agree on it only weakly (correlation about 0.03).
- **Echo complexity mostly reads ongoing activity**, not the poke (sham checks), so it is not in the rule.
- **Immobilised worms under light every 30 s.** A model that passes here failed on freely moving worms
  from another lab (README, test T). The benchmark speaks for these conditions.
- **The poked neuron's drive is given.** The benchmark tests what the rest of the brain does, not how
  a neuron answers light. A repeat poke within 2 minutes gets about half the first response, which the
  drive already contains.
- **What a pass means for the pokes.** Known errors were put into real held-out worms' own responses
  and scored as a copy would be (README, "The ruler's resolution"). The poked neuron misattributed in
  half the pulses, or every response 1.5 times too big, is caught in 6 of 6 pools. Errors of about a
  quarter often pass. A pass means "within about 25% of a real worm on these levels", not "faithful".

## Data and citation

Randi, F., Sharma, A. K., Dvali, S. & Leifer, A. M. (2023). Neural signal propagation atlas of
*Caenorhabditis elegans*. *Nature* 623, 406-414. https://doi.org/10.1038/s41586-023-06683-4. The data is CC BY 4.0 and is not redistributed here:
each user downloads and converts it locally. Reports contain only scores.
