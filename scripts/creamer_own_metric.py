import numpy as np
from nematica.data.safe_pickle import load
meas = load('data/external/creamer_lds/measured_stams.pkl')
n = meas['train'].shape[0]
diag = np.eye(n, dtype=bool)
tr, te = meas['train'].copy(), meas['test'].copy()
tr[diag] = te[diag] = np.nan
def nan_corr(a, b):
    a, b = a.ravel(), b.ravel(); m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m] - a[m].mean(), b[m] - b[m].mean()
    return float(np.mean(a * b) / a.std() / b.std()), int(m.sum())
tt, npairs = nan_corr(tr, te)
print(f"train-test STAM correlation {tt:.3f} over {npairs} pairs")
for name in ("connectome_constrained", "fully_connected", "shuffled_constrained"):
    m = load(f'data/external/creamer_lds/{name}.pkl')
    A = np.asarray(m.dynamics_weights, float); B = np.asarray(m.dynamics_input_weights, float)
    C = np.asarray(m.emissions_weights, float); D = np.asarray(m.emissions_input_weights, float)
    L = m.dynamics_input_lags
    Bk = [B[:, k * n:(k + 1) * n] for k in range(L)]       # input k frames ago
    T = int(30 * m.sample_rate)
    stam = np.zeros((n, n))
    for s in range(n):
        x = np.zeros(n); acc = np.zeros(n)
        for t in range(T):
            x = (A @ x if t else x) + (Bk[t][:, s] if t < L else 0)
            acc += C @ x + (D[:, s] if t == 0 else 0)
        stam[:, s] = acc / m.sample_rate
    stam[diag] = np.nan
    c, _ = nan_corr(stam, te)
    print(f"{name:24s} corr with test {c:.3f}   relative to train-test {c / tt:.2f}")
