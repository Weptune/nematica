"""Exploratory (8 Nov 2026, after T1 was abandoned and after T3 was seen): the light/activity split with
activity measured only from network drive (no lagged own response, which the T3 synthetic check showed
creates a spurious activity effect). Light share here = (beta_L - beta_A * own) / beta_L: the part of the
direct-poke drop not explained by the activity it caused at the per-SD rate measured without light.
Checked on synthetic truths first (none, tool, neuron, mixed), then the worms. Output appended to
docs/figures/light_or_activity.txt."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
import run_light_or_activity as R  # noqa: E402
import run_week1 as W  # noqa: E402
from nematica import tiring_sim as TM  # noqa: E402


def keyed_net(ws):
    per = []
    for wi, w in enumerate(ws):
        rs = TM.rows_net(w)
        for r in rs:
            r["key"] = f"{wi}_{r['unit']}"
        if rs:
            per.append(rs)
    return per


def run(per, label, nb=1000, ns=0):
    res = TM.t1(per, n_boot=nb, n_shuf=ns, share=TM.light_share_net)
    R.log(f"EXPLORATORY net-drive split, {label}: n {res['n']} (L=1 {res['n_L']}); bL {res['b'][0]:+.3f} [{res['lo'][0]:+.3f}, {res['hi'][0]:+.3f}]; "
          f"bA(net) {res['b'][1]:+.3f} [{res['lo'][1]:+.3f}, {res['hi'][1]:+.3f}]; own act {res['A_dir']:.2f}; "
          f"light share {res['S']:.2f} [{res['S_lo']:.2f}, {res['S_hi']:.2f}]" + (f"; p(L) {res['p_L']:.4f}" if ns else ""))


if __name__ == "__main__":
    sc = R.schedules()
    if sys.argv[1:] == ["synth"]:
        for name, truth, kw in [("none", "none", {}), ("tool tau10", "tool", dict(h=0.35)), ("tool tau2", "tool", dict(h=0.35, tau=240)),
                                ("neuron tau10", "neuron", dict(kappa=0.5)), ("neuron tau40", "neuron", dict(kappa=0.5, tau=4800)),
                                ("mixed tau10", "mixed", dict(h=0.6, kappa=0.25))]:
            for s in range(4):
                run(keyed_net(R.synth_atlas(sc, truth, 700 + s, **kw)), f"SYNTHETIC {name} atlas {s}", nb=500)
    else:
        run(keyed_net([R.wrap(w) for w in W.load_worms()]), "WORMS (wild type)", nb=2000, ns=2000)
