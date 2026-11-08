"""Calibration of the brain-likeness test (pre-registered; README "Brain-likeness test").

  python scripts/calibrate_brainlike.py worms        # held-out worm groups against an 83-worm reference
  python scripts/calibrate_brainlike.py systems      # random RNN, lab network with slow drives, random GRU (ONNX)
Writes docs/figures/brainlike_calibration.json (scores only) and the full results to
nematica/brainlike/calibration/<name>.json (summary numbers; scripts/seed_brainlike_board.py
puts them on a website leaderboard).
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica import annlab as L  # noqa: E402
from nematica.brainlike import reference as REF  # noqa: E402
from nematica.brainlike.networks import RateRNN, load_network  # noqa: E402
from nematica.brainlike.signatures import SIGNATURES, measure  # noqa: E402
from nematica.brainlike.test import BrainLike, run_python, run_test, score  # noqa: E402

OUT = ROOT / "docs" / "figures" / "brainlike_calibration.json"
warnings.filterwarnings("ignore", category=RuntimeWarning)


def save(key, val):
    d = json.loads(OUT.read_text()) if OUT.exists() else {}
    d[key] = val
    OUT.write_text(json.dumps(d, indent=1, default=float))


FULL = ROOT / "nematica" / "brainlike" / "calibration"


def save_full(name, res, description):
    import re
    FULL.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    (FULL / f"{slug}.json").write_text(json.dumps({"name": name, "description": description, "result": res},
                                                  indent=1, default=float))


def short(res):
    return {"score": res["score"], "valid": res["valid"], "problems": res["problems"],
            "signatures": {k: {"value": v["value"], "inside": v["inside"], "distance": v["distance"]}
                           for k, v in res["signatures"].items()},
            "poked_response": res.get("measured", {}).get("poked_response")}


def worms():
    from nematica.data.pumpprobe import load_pumpprobe_dir
    from nematica.roles import role
    recs = sorted(load_pumpprobe_dir(ROOT / "data/raw/randi2023_wt_npz"), key=lambda r: r.uid)
    rng = np.random.default_rng(11)
    out = []
    for h in range(3):
        idx = rng.permutation(len(recs))
        held, rest = [recs[i] for i in sorted(idx[:30])], [recs[i] for i in sorted(idx[30:])]
        ref = {"group_size": 30, "signatures": {}}
        vals = {k: [] for k in SIGNATURES}
        g = np.random.default_rng(100 + h)
        for _ in range(200):                                  # as the reference (amendment 3)
            pick = [rest[i] for i in sorted(g.choice(len(rest), 30, replace=False))]
            m = measure(pick, valid_fn=lambda c: role(c) is not None)
            for k in vals:
                vals[k].append(m[k])
        for k, v in vals.items():
            v = np.asarray(v)[np.isfinite(v)]
            ref["signatures"][k] = {"median": float(np.median(v)), "p2_5": float(np.percentile(v, 2.5)),
                                    "p97_5": float(np.percentile(v, 97.5))}
        # the correction uses the pool the reference groups come from (83 here)
        fpc_pool = len(rest)
        for k in ref["signatures"]:
            r = ref["signatures"][k]
            f = (1.0 / np.sqrt(1.0 - 30 / fpc_pool)) / (1.0 / np.sqrt(1.0 - 30 / 113))
            r["p2_5"] = r["median"] - (r["median"] - r["p2_5"]) * f
            r["p97_5"] = r["median"] + (r["p97_5"] - r["median"]) * f
        m = measure(held, valid_fn=lambda c: role(c) is not None)
        res = score(m, ref)
        print(f"held-out group {h}: {res['score']} of 8 inside", {k: v["inside"] for k, v in res["signatures"].items()}, flush=True)
        res["how"] = "30 real worms held out of the reference (scored against the other 83)"
        save_full(f"Real worms held out of the reference, group {h + 1}", res,
                  "30 real C. elegans recordings from the atlas, held out of the reference: the reference ranges "
                  "here come from the other 83 worms. Shows what a real nervous system scores.")
        out.append({"score": res["score"], "signatures": {k: {"value": v["value"], "inside": v["inside"],
                                                               "distance": v["distance"]} for k, v in res["signatures"].items()}})
    save("held_out_worms", out)


class LabBrain(BrainLike):
    """The project's artificial-lab network (nematica.annlab) as a Python system: tanh units, sparse
    random weights, optional slow hidden drives no recording sees."""
    def __init__(self, share=0.0, seed=0):
        self.br = L.make_brain(n=120, rho=1.3, share=share, seed=seed)
        self.n_units, self.step_seconds = 120, 0.5
        self.calibrate_push, self.push_strength = True, L.KICK
        self.name = f"lab network (slow drives share {share})"

    def run(self, steps, record, pushes, push_steps, rng):
        br, n = self.br, self.br.n
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


def gru_onnx(path, n=120, seed=0):
    """A random GRU cell, exported so the test's input reaches one unit each: the cell runs on its own state
    (no external input) and input[:, i] is added to hidden unit i (amendment 3: the first version fed the
    input through the cell's input weights, so a push to unit i reached every unit)."""
    import torch
    torch.manual_seed(seed)

    class Step(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.cell = torch.nn.GRUCell(n, n)

        def forward(self, state, input):            # noqa: A002
            return self.cell(torch.zeros_like(input), state) + input
    m = Step().eval()
    torch.onnx.export(m, (torch.zeros(1, n), torch.zeros(1, n)), str(path), input_names=["state", "input"],
                      output_names=["next_state"], dynamic_axes={"state": {0: "b"}, "input": {0: "b"}, "next_state": {0: "b"}},
                      opset_version=17, dynamo=False)
    return path


def gru():
    p = gru_onnx(Path("/tmp/random_gru.onnx"))
    net = load_network(p, "random GRU (ONNX)")
    t = time.time()
    res = run_test(net, log=lambda m: print("  ", m, flush=True))
    print(f"random GRU (ONNX): score {res['score']} valid {res['valid']} ({time.time() - t:.0f} s)", flush=True)
    save("random GRU (ONNX)", short(res))
    save_full("Random GRU, 120 units (ONNX)", res, GRU_ABOUT)


GRU_ABOUT = "A PyTorch GRU cell with 120 units and random weights, exported to ONNX. A baseline."


def systems():
    br = L.make_brain(n=120, rho=1.3, seed=0)
    # the lab adds noise 0.3 after the leak; here noise enters inside it, so 0.3 / LEAK matches
    nets = {"random tanh RNN (npz)": RateRNN(br.W, br.b, leak=L.LEAK, nonlinearity="tanh", noise_sd=0.3 / L.LEAK, name="random tanh RNN")}
    for name, net in nets.items():
        t = time.time()
        res = run_test(net, log=lambda m: print("  ", m, flush=True))
        print(f"{name}: score {res['score']} valid {res['valid']} ({time.time() - t:.0f} s)", flush=True)
        save(name, short(res))
        save_full("Random tanh RNN, 120 units", res, "120 tanh units, sparse random weights (spectral radius 1.3), leak 0.5, "
                  "input noise 0.6 per step. A baseline: an untrained recurrent network.")
    for share in (0.0, 0.4):
        sysm = LabBrain(share=share)
        t = time.time()
        res = run_python(sysm, log=lambda m: None)
        print(f"{sysm.name}: score {res['score']} valid {res['valid']} ({time.time() - t:.0f} s)", flush=True)
        save(sysm.name, short(res))
        save_full("Artificial-lab network with 5 s hidden drives" if share else "Artificial-lab network, plain", res, "The project's artificial-lab network: 120 tanh units, sparse random weights"
                  + (", plus slow hidden drives no recording sees (share 0.4, time constant 5 s)" if share else "") + ". A baseline.")
    p = gru_onnx(Path("/tmp/random_gru.onnx"))
    net = load_network(p, "random GRU (ONNX)")
    t = time.time()
    res = run_test(net, log=lambda m: print("  ", m, flush=True))
    print(f"random GRU (ONNX): score {res['score']} valid {res['valid']} ({time.time() - t:.0f} s)", flush=True)
    save("random GRU (ONNX)", short(res))
    save_full("Random GRU, 120 units (ONNX)", res, GRU_ABOUT)


if __name__ == "__main__":
    {"worms": worms, "systems": systems, "gru": gru}[sys.argv[1]]()
