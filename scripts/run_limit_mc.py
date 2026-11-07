"""Does the best watcher reach the Cramer-Rao limit? Monte Carlo on a small latent network.

Fits the correct model class (Whittle MLE, generic starts, best of 2) to `reps` independent
rest recordings of T frames; compares the empirical spread of the poke-response estimates
with the bound, and reports agreement for the MLE, the VAR watcher and the bound.
"""
import sys, json, time
import numpy as np
from nematica import limits as L

T, reps = int(sys.argv[1]), int(sys.argv[2])
out = sys.argv[3]
net = L.random_net(n=6, k=1, seed=4, drive_load=1.0)
G = L.offdiag(L.poke_response(net.F, 6))
cov, info = L.crb_G(net, T)
E, V = [], []
t0 = time.time()
for r in range(reps):
    y = L.simulate(net, T, np.random.default_rng(1000 * T + r))
    best = None
    for s in range(2):
        Gh, _, loss = L.whittle_fit([y], 6, 1, steps=800, lr=0.01, band=max(4, T // 1000), seed=s)
        if best is None or loss < best[1]:
            best = (Gh, loss)
    E.append(L.offdiag(best[0]))
    V.append(L.offdiag(L.var_watcher([y], 6)))
    print(r, round(time.time() - t0), flush=True)
E, V = np.array(E), np.array(V)
res = dict(T=T, reps=reps, crb_mean_var=float(np.diag(cov).mean()),
           mle_mean_var=float(E.var(0).mean()), mle_bias2=float(((E.mean(0) - G) ** 2).mean()),
           ratio_median=float(np.median(E.var(0) / np.diag(cov))),
           var_bias2=float(((V.mean(0) - G) ** 2).mean()), var_mean_var=float(V.var(0).mean()),
           agree_bound=L.agreement_from_cov(G, cov),
           agree_mle=float(np.mean([np.corrcoef(e, G)[0, 1] for e in E])),
           agree_var=float(np.mean([np.corrcoef(e, G)[0, 1] for e in V])))
json.dump(res, open(out, "w"), indent=1)
print(res)
