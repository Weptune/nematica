"""Study 3 check: with noise_sd = 0, the noisy system functions reproduce Study 2's exactly; with noise,
repeats differ even with identical contexts (the noise generates variability)."""
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.persist import inputs as PI  # noqa: E402
from nematica.slow import inputs as I  # noqa: E402


def main():
    torch.manual_seed(0)
    n = 64
    model = (torch.nn.Embedding(50, 16), torch.nn.GRUCell(16, n), n)
    data = np.random.default_rng(0).integers(0, 50, 20000)
    a, sa = I.char_repeats(model, data, 10000, 40, R=4, seed=1)
    b, sb = PI.char_repeats_noisy(model, data, 10000, 40, R=4, seed=1, noise_sd=0.0)
    print("char, noise 0: identical", np.array_equal(a, b) and sa == sb)
    rng = np.random.default_rng(0)
    clip = rng.integers(0, 1000, 32)
    ctx = [rng.integers(0, 1000, 64)] * 3                   # identical contexts
    x, _, _ = I.lm_repeats("EleutherAI/pythia-14m", clip, ctx)
    y, _, _ = PI.lm_repeats_noisy("EleutherAI/pythia-14m", clip, ctx, noise_sd=0.0)
    print("pythia-14m, noise 0: identical", np.array_equal(x, y))
    z, _, _ = PI.lm_repeats_noisy("EleutherAI/pythia-14m", clip, ctx, noise_sd=0.2, noise_seed=3)
    r = z.reshape(3, 32, -1)
    print("noise 0.2, identical contexts: repeats differ", float(np.abs(r[0] - r[1]).mean()) > 0,
          "| without noise they are identical:", np.array_equal(x.reshape(3, 32, -1)[0], x.reshape(3, 32, -1)[1]))


if __name__ == "__main__":
    main()
