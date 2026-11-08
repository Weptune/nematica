"""Middle-ground calibration of the brain-likeness test (README "Brain-likeness test", amendment 1 (c),
registered 9 Nov 2026 before running).

  python scripts/calibrate_brainlike_middle.py atlas        # M1 emulator, M2 watching copy, on atlas templates
  python scripts/calibrate_brainlike_middle.py lab          # M3 lab network, slow drives at 40 s
  python scripts/calibrate_brainlike_middle.py tasks        # M4 to M7 task-trained RNNs and their untrained controls
  python scripts/calibrate_brainlike_middle.py spiking      # M8, M9
  python scripts/calibrate_brainlike_middle.py transformer  # M10, M11

Full results go to nematica/brainlike/calibration/ (summary numbers only), scores to
docs/figures/brainlike_calibration.json (key "middle").
"""
import json
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nematica import annlab as L  # noqa: E402
from nematica.brainlike.protocol import Protocol, make_schedule, to_recordings  # noqa: E402
from nematica.brainlike.signatures import Run, SIGNATURES, measure, poked_response  # noqa: E402
from nematica.brainlike.test import _search_push, evaluate, run_python, score  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "docs" / "figures" / "brainlike_calibration.json"
FULL = ROOT / "nematica" / "brainlike" / "calibration"


def save(name, res, description, key):
    FULL.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    (FULL / f"{slug}.json").write_text(json.dumps({"name": name, "description": description, "result": res},
                                                  indent=1, default=float))
    d = json.loads(OUT.read_text()) if OUT.exists() else {}
    d.setdefault("middle", {})[key] = {
        "name": name, "score": res["score"], "valid": res["valid"], "problems": res["problems"],
        "inside": {k: v["inside"] for k, v in res["signatures"].items()},
        "distance": {k: v["distance"] for k, v in res["signatures"].items()}}
    OUT.write_text(json.dumps(d, indent=1, default=float))
    ins = [k for k, v in res["signatures"].items() if v["inside"]]
    print(f"{key} {name}: score {res['score']} valid {res['valid']} inside {ins} {res['problems']}", flush=True)


# ---------------------------------------------------------------- M1, M2: atlas templates
def atlas():
    import yaml
    import nematica.systems.causal_models as causal
    from nematica.data.pumpprobe import load_pumpprobe_dir
    from nematica.roles import role
    from run_same_worms import make_model
    causal.NORM = "fluct"
    recs = {r.uid: r for r in load_pumpprobe_dir(ROOT / "data/raw/randi2023_wt_npz")}
    from nematica.data.splits import load_folds
    folds = load_folds(ROOT / "configs/splits/pumpprobe_cv3.yaml")["folds"]
    specs = {"M1": ("hybrid_kernels_slow6d_indivslow1_hp_memfix_diag_hsd1", "Worm emulator (minimal recipe)",
                    "The project's worm emulator: slow interacting brain-wide states, individual variation, causal "
                    "links learned from stimulation, neurons observed one by one. Fitted on the atlas worms of the "
                    "other two pools and simulated on held-out worm templates. Built on these worms: not independent."),
             "M2": ("var3_spontaneous", "Watching copy (VAR(3) from rest)",
                    "A linear model fitted to the atlas worms' stimulation-free activity (what watching teaches), "
                    "simulated on held-out worm templates.")}
    for key, (spec, name, about) in specs.items():
        t0 = time.time()
        sims = []
        for fi, pool_uids in enumerate(folds):
            rest = sorted(u for f in folds if f is not pool_uids for u in f)
            val_uids = rest[::5]
            train = [recs[u] for u in rest if u not in val_uids]
            val = [recs[u] for u in val_uids]
            m = make_model(spec).fit(train, val)
            sims += [m.simulate(recs[u], np.random.default_rng(50000 + 1000 * fi + i)) for i, u in enumerate(pool_uids)]
            print(f"  {key} fold {fi}: {len(sims)} simulated worms ({time.time() - t0:.0f} s)", flush=True)
        sims.sort(key=lambda r: r.uid)
        g = np.random.default_rng(11)
        idx = g.permutation(len(sims))
        for gi in range(3):
            pick = [sims[i] for i in sorted(idx[30 * gi:30 * gi + 30])]
            m = measure(pick, valid_fn=lambda c: role(c) is not None)
            res = score(m, check_push=True)
            res.update({"measured": {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()},
                        "how": "simulated on 30 held-out atlas worm templates, measured exactly as worms"})
            save(f"{name}, group {gi + 1}", res, about, f"{key}.g{gi + 1}")


# ---------------------------------------------------------------- generic-schedule systems
class LabBrain:
    """annlab network as a Python system (as in calibrate_brainlike.py), optionally slow drives."""
    calibrate_push = True

    def __init__(self, br, name, step_seconds=0.5):
        self.br, self.name = br, name
        self.n_units, self.step_seconds = br.n, step_seconds
        self.push_strength = L.KICK

    def reset(self):
        pass

    def run(self, steps, record, pushes, push_steps, rng):
        br, n = self.br, self.br.n
        self.reset()
        k = 0 if br.D is None else br.D.shape[1]
        x, s = np.zeros(n), np.zeros(k)
        for _ in range(400):
            s = br.drive_step(s, rng)
            x = br.step(x, s, rng.standard_normal(n))
        on = {}
        for t, u in pushes:
            for d in range(push_steps):
                on[t + d] = u
        out = np.empty((steps, len(record)))
        for t in range(steps):
            s = br.drive_step(s, rng)
            x = br.step(x, s, rng.standard_normal(n))
            if t in on:
                x[on[t]] += self.push_strength
            out[t] = np.tanh(x)[record] + br.r * rng.standard_normal(len(record))
        return out


def lab():
    br = L.make_brain(n=120, rho=1.3, share=0.4, tau=80.0, seed=0)
    sysm = LabBrain(br, "Artificial-lab network with 40 s hidden drives")
    res = run_python(sysm, log=lambda m: None)
    save(sysm.name, res, "The artificial-lab network (120 tanh units, sparse random weights) with slow hidden drives "
         "at the worm's timescale (40 s time constant) carrying 40% of each unit's input variance.", "M3")


class TaskLab(LabBrain):
    def reset(self):
        self.br._task = None


def tasks():
    import run_ann_trained as T
    about = {"flipflop": "a 3-bit flip-flop memory task (Sussillo and Barak 2013)",
             "cdi": "context-dependent integration (Mante et al. 2013)"}
    for key, task, trained in (("M4", "flipflop", True), ("M5", "flipflop", False), ("M6", "cdi", True), ("M7", "cdi", False)):
        br = T.make_task_brain(task, trained)
        nm = f"RNN {'trained on' if trained else 'before training on'} {'a flip-flop task' if task == 'flipflop' else 'context-dependent integration'}"
        sysm = TaskLab(br, nm)
        res = run_python(sysm, log=lambda m: None)
        save(nm, res, f"The artificial-lab network (120 tanh units) {'trained on' if trained else 'before training on'} "
             f"{about[task]}, performing the task throughout (the task inputs are its unrecorded drives).", key)


def _batch_test(simulate, n_units, name, extra, calibrate=True, base=1.0):
    """simulate(amplitude, schedule, rng) -> activity (runs, steps, analysis units)."""
    rng = np.random.default_rng(0)
    amp = base
    if calibrate:
        pilot = make_schedule(n_units, 0.5, Protocol(runs=6, minutes=8.0))

        def response(a):
            act = simulate(a, pilot, np.random.default_rng(int(rng.integers(1 << 31))))
            return poked_response([Run(x) for x in to_recordings(act, pilot, np.random.default_rng(1))])
        amp, _ = _search_push(response, base)
    sch = make_schedule(n_units, 0.5)
    t0 = time.time()
    act = simulate(amp, sch, rng)
    res = evaluate(act, sch, "system run by the test (batched)", {"push_strength": amp, "seconds": round(time.time() - t0, 1), **extra})
    return res


def spiking():
    from nematica import spiking as S
    W0 = S.base_weights(0)
    for key, variant, nm in (("M8", "S0", "Spiking network, plain"), ("M9", "S1", "Spiking network with adaptation")):
        def sim(amp, sch, rng, variant=variant):
            R, T = len(sch.runs), sch.steps
            units = np.asarray(sch.units)
            kt = -np.ones((R, T), int)
            for i, run in enumerate(sch.runs):
                for st, p in run["pushes"]:
                    kt[i, st:st + sch.push_steps] = units[p]
            y = S.simulate(np.repeat(W0[None], R, axis=0), kt, variant=variant, frames=T, burn=400,
                           seed=int(rng.integers(1 << 30)))
            return y[:, :, units].astype(np.float32)
        res = _batch_test(sim, S.N, nm, {"variant": variant}, calibrate=False)
        save(nm, res, f"120 leaky integrate-and-fire neurons (96 excitatory, 24 inhibitory), 5 ms steps, read out "
             f"through a calcium-like filter at 0.5 s; variant {variant}"
             + (" (spike-frequency adaptation decaying over 10 min)" if variant == "S1" else "")
             + ". Pushed with its own fixed current for 2 s.", key)


def transformer():
    import torch
    from nematica import tlab
    torch.set_num_threads(2)
    for key, steps, nm in (("M10", 3000, "Transformer trained on a synthetic language"),
                           ("M11", 0, "Transformer, untrained")):
        net, loss = tlab.base_model(steps=steps, seed=0)
        net.eval()
        D, V, WIN, LAYER = net.cfg["D"], net.cfg["V"], net.cfg["band"], 1

        @torch.no_grad()
        def sim(amp, sch, rng, net=net):
            R, T = len(sch.runs), sch.steps
            units = np.asarray(sch.units)
            g = torch.Generator().manual_seed(int(rng.integers(1 << 30)))
            tok = torch.randint(0, V, (R, 1), generator=g)
            patch = torch.zeros(R, T + 400 + 1, D)
            push = np.full((R, T), -1)
            for i, run in enumerate(sch.runs):
                for st, p in run["pushes"]:
                    push[i, st:st + sch.push_steps] = units[p]
            out = np.empty((R, T, len(units)), np.float32)
            for t in range(-400, T):
                pos = tok.shape[1] - 1
                if t >= 0:
                    on = np.flatnonzero(push[:, t] >= 0)
                    if on.size:
                        patch[torch.tensor(on), pos, torch.tensor(push[on, t])] += amp
                lo = max(0, tok.shape[1] - WIN)
                logits, rec = net(tok[:, lo:], {("resid", LAYER): patch[:, lo:tok.shape[1]]})
                if t >= 0:
                    out[:, t] = rec[("resid", LAYER)][:, -1, units].numpy()
                nxt = torch.multinomial(torch.softmax(logits[:, -1], -1), 1, generator=g)
                tok = torch.cat([tok, nxt], 1)
                if tok.shape[1] > WIN + 1:
                    keep = tok.shape[1] - (WIN + 1)
                    tok = tok[:, keep:]
                    patch = torch.cat([patch[:, keep:], torch.zeros(R, keep, D)], 1)
            return out
        res = _batch_test(sim, D, nm, {"training_steps": steps, "loss": loss})
        save(nm, res, f"A small causal transformer (4 blocks, width {D}, local attention over {WIN} tokens) "
             + ("trained to predict a synthetic language with slow hidden states" if steps else "with random weights")
             + "; it generates its own tokens, one per step; the 64 units of the residual stream after block 2 are "
             "recorded and pushed.", key)


if __name__ == "__main__":
    {"atlas": atlas, "lab": lab, "tasks": tasks, "spiking": spiking, "transformer": transformer}[sys.argv[1]]()
