"""Synthetic check of the tests stage logic (SLOW_LOG, "Synthetic check of the tests stage", and the S-R2
revision): known gaps must give known verdicts. Writes only the git-ignored *_dry files."""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slow_run as S

rng = np.random.default_rng(0)
mice = {}
for i in range(58):
    m1 = float(rng.normal(0.5, 0.1)); m2 = float(np.exp(rng.normal(1.0, 0.3)))
    sp = lambda: {"M1": m1 + rng.normal(0, 0.03), "M2": m2 * np.exp(rng.normal(0, 0.1)), "no_shared": False,
                  "no_locked": False, "int_ceiling": False}
    mice[f"m{i}"] = dict(id=f"m{i}", rank=i, M1=m1, M2=m2, no_shared=False, no_locked=False, int_ceiling=False,
                         lock_ceiling=False, ti=m2 * 3, tl=3.0, split={"odd": sp(), "even": sp()},
                         profile={"bins_per_tau": float(rng.uniform(1.5, 20)), "count_per_bin": 0.066,
                                  "noise": 0.9, "rate_log_sd": 1.2}, repeats=20, units=300)
    if i >= 32:
        mice[f"m{i}"]["shuffled"] = {"M1": m1, "M2": m2 * 2.5, "tl": 1.2, "ti": m2 * 3 * 1.05, "no_shared": False,
                                     "no_locked": False}
with open(S.OUT / "mice_dry.jsonl", "w") as f:
    for r in mice.values():
        f.write(json.dumps(r) + "\n")
rows, med = S.mice_table(dry=True)
ais = []


def add(fam, run, m, m1, m2, **kw):
    base = dict(family=fam, run=run, id=m["id"], instance=m["instance"],
                group=m["group"] if fam in S.MOVIE_FAMS else None, M1=m1, M2=m2, no_shared=False, no_locked=False,
                int_ceiling=False, lock_ceiling=False, reached=True)
    base.update(kw)
    ais.append(base)


for m in rows:
    i = m["instance"]
    add("A2", f"i{i}", m, m["M1"] - 0.3, m["M2"] / 3)                      # clear gap on both: confirmed
    add("A3", f"i{i}", m, m["M1"] + 0.3, m["M2"] * 3)                      # AI above: refuted
    for gain, dm in zip(S.GAINS, np.linspace(-0.4, 0.4, len(S.GAINS))):    # grid spans the mouse: d = 0
        add("A1", f"i{i}-gain{gain}", m, m["M1"] + dm, m["M2"] * np.exp(dm))
    for gain in S.GAINS:                                                   # A4: no shared part at all
        add("A4", f"i{i}-gain{gain}", m, 0.0, np.nan, no_shared=True)
    add("A5", f"i{i}", m, 0.01, np.nan)                                    # no internal part on M2
    for size in ("pythia-14m", "pythia-160m", "pythia-410m", "pythia-1b"):  # A6, 4 sizes, gap, inst 2 none
        gap = 0.3 if i < 2 else 0.0
        add("A6", f"{size}-i{i}", m, m["M1"] - gap - (0.05 if size != "pythia-1b" else 0.0), m["M2"] / (3 if i < 2 else 1))
    for size in ("mamba-130m", "mamba-370m"):                              # A7: unreached everywhere
        add("A7", f"{size}-i{i}", m, m["M1"] - 0.3, m["M2"] / 3, reached=False)
    for share in S.SLOW_SHARES:
        for tau in S.SLOW_TAUS_S:
            off = abs(share - 0.2) + abs(tau - 1.0)
            add("A1-slow", f"i{i}-share{share}-tau{tau}", m, m["M1"] - off * 0.5 + rng.normal(0, 0.02), m["M2"] * np.exp(-off))
        for fr in S.FAST_FRAMES:
            add("A1-fast", f"i{i}-share{share}-tau{fr}f", m, m["M1"] - 0.2 + share * 0.2, m["M2"] / 4)
    for gain in S.NOISE_GAINS:
        for nz in S.NOISES:
            add("A1-noise", f"i{i}-share{nz}-tau{gain}g", m, m["M1"] - 0.3 + nz * 0.1, m["M2"] / 3)
    for var, shift in (("x0.5", 0.0), ("x2.0", 0.4), ("driven", 0.0)):     # playback moves M2 a lot
        add("A1-play", f"i{i}-{var}", m, m["M1"] - 0.4 + 0.05 * (S.GAINS.index(S.PLAY_GAIN) - 3) * 0 + 0.0,
            m["M2"] * np.exp(-0.4 + shift * 10))
with open(S.OUT / "ais_dry.jsonl", "w") as f:
    for r in ais:
        f.write(json.dumps(r) + "\n")
S.stage_tests(dry=True)
d = json.load(open(S.OUT / "tests_dry.json"))
for fam in S.RUNS_PER_FAMILY:
    print(fam, {m: (d["H1"][fam][m].get("verdict"), d["H1"][fam][m].get("counted", True)) for m in ("M1", "M2")})
print("claims", {k: v.get("holds") for k, v in d["claims"].items()})
print("claim 1", d["claims"]["1_more_internal_state"])
print("H2", {k: (v.get("chosen"), v.get("equivalent_both")) if isinstance(v, dict) else v for k, v in d["H2"].items()
             if k != "train_cells"})
print("playback", d["nuisance_playback_M2_sensitive"], "shuffled passes", d["validity_shuffled"]["passes"])
