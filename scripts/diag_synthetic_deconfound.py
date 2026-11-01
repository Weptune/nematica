"""Does removing the top principal components before fitting rescue learning cause by watching
under shared hidden drives? Synthetic worm of scripts/run_synthetic_watch.py, 10 hours, half
the neurons seen per recording, 30% never seen. Usage: python scripts/diag_synthetic_deconfound.py"""
import sys, importlib.util, warnings
warnings.filterwarnings("ignore")
import numpy as np
spec = importlib.util.spec_from_file_location("sw", "scripts/run_synthetic_watch.py"); sw = importlib.util.module_from_spec(spec); spec.loader.exec_module(sw)
def project_out(y, k):
    """Remove the top-k principal components of the observed neurons from one recording."""
    if k == 0: return y
    obs = np.isfinite(y[0]); z = y[:, obs] - y[:, obs].mean(0)
    U, S, Vt = np.linalg.svd(z, full_matrices=False)
    z = z - (U[:, :k] * S[:k]) @ Vt[:k]
    out = y.copy(); out[:, obs] = z; return out
for model in ("connectome_constrained", "fully_connected"):
    z = np.load(f"data/external/creamer_lds/{model}.npz"); A, Q, R = z["A"], z["Q"], z["R"]; n = len(A)
    Lq = np.sqrt(np.diag(Q)) * np.eye(n); sr = np.sqrt(np.diag(R)); K = sw.true_K(A)
    hidden = np.random.default_rng(0).random(n) < 0.3
    mask = ~np.eye(n, dtype=bool) & ~hidden[:, None] & ~hidden[None, :]
    for share in (0.0, 0.05, 0.10):
        D = sw.shared_drive(Lq, share, 3, np.random.default_rng(7)) if share else None
        g = np.random.default_rng(1); recs = []
        for r in range(16):                                   # 10 hours
            obs = (g.random(n) < 0.5) & ~hidden
            y = sw.simulate(A, Lq, sr, sw.FRAMES, g, D=D); y[:, ~obs] = np.nan; recs.append(y)
        res = []
        for k in (0, 1, 3, 5):
            W = sw.fit_watching([project_out(y, k) for y in recs], n)
            res.append(f"k={k}: {sw.score(sw.true_K(W), K, mask):.3f}")
        print(model, f"drive {share:.2f}", "  ".join(res), flush=True)
