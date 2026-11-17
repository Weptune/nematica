"""Amendment S8 check: the truncated language-model path in nematica.slow.inputs.lm_repeats (load at the
checkpoint's precision, keep layers up to the recorded one, cast to float32) gives the same recorded units
as the path used before S8 (load the whole model in float32, run every layer).

Checked on Pythia-14m and Pythia-70m (cached locally) and on two small randomly initialised Mamba models
saved in float32 and float16, so both architectures and both checkpoint precisions are covered without
downloading anything. Prints the largest absolute difference per model; exits nonzero if any exceeds 1e-6.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.slow import inputs as I  # noqa: E402


def old_path(model_name, clip, contexts, keep=480, seed=0):
    """lm_repeats as it was before amendment S8 (copied from commit history)."""
    from transformers import AutoModelForCausalLM
    m = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float32).eval()
    C = len(clip)
    if "mamba" in model_name:
        blocks = m.backbone.layers
        L = len(blocks) // 2
        target = blocks[L].mixer.out_proj
        grab = lambda mod, inp, out: buf.append(inp[0][0, -C:].detach().float().numpy())
    else:
        blocks = m.gpt_neox.layers
        L = len(blocks) // 2
        target = blocks[L].mlp.act
        grab = lambda mod, inp, out: buf.append(out[0, -C:].detach().float().numpy())
    buf = []
    h = target.register_forward_hook(grab)
    with torch.no_grad():
        for ctx in contexts:
            m(torch.tensor(np.concatenate([ctx, clip])[None], dtype=torch.long))
    h.remove()
    units = buf[0].shape[1]
    cols = np.sort(np.random.default_rng(seed).choice(units, min(keep, units), replace=False))
    return np.concatenate([b[:, cols] for b in buf], 0).astype(np.float32)


def main():
    torch.set_num_threads(2)
    rng = np.random.default_rng(0)
    clip = rng.integers(0, 1000, 64)
    contexts = [rng.integers(0, 1000, 128) for _ in range(3)]
    names = ["EleutherAI/pythia-14m", "EleutherAI/pythia-70m"]
    tmp = Path(tempfile.mkdtemp(prefix="s8_"))
    from transformers import MambaConfig, MambaForCausalLM
    for dt in (torch.float32, torch.float16):
        torch.manual_seed(1)
        cfg = MambaConfig(vocab_size=1000, hidden_size=64, state_size=8, num_hidden_layers=6)
        d = tmp / f"mamba-tiny-{str(dt).split('.')[-1]}"
        MambaForCausalLM(cfg).to(dt).save_pretrained(d)
        names.append(str(d))
    worst = 0.0
    for n in names:
        a = old_path(n, clip, contexts)
        b, starts, meta = I.lm_repeats(n, clip, contexts)
        diff = float(np.max(np.abs(a - b)))
        worst = max(worst, diff)
        print(f"{Path(n).name}: shape {a.shape} vs {b.shape}, layer {meta['layer']}, "
              f"max abs difference {diff:.3g}, identical {np.array_equal(a, b)}")
    print("PASS" if worst <= 1e-6 else "FAIL")
    sys.exit(0 if worst <= 1e-6 else 1)


if __name__ == "__main__":
    main()
