"""Study 3 check: windowed measures equal Study 2 half-clip M1 at W=2, and streamed equals materialised."""
import sys, numpy as np
sys.path.insert(0, "/home/claude/nematica")
from nematica.slow import synthetic as S, stream as ST, measures as M
from nematica.persist import measures as PM
rng = np.random.default_rng(3)
A, starts = S.continuous(rng, R=8, T=700, N=48, share=0.4, tau_locked=10, tau_internal=30, lead=500)
k = {"hold": 1, "bin_steps": 1.0, "mean_count": 0.5, "gain": 1.0, "rate_log_sd": 0.3}
rec = ST.Recorder(A, starts, 700, k, seed=5)
p1 = rec.pass1(); pos = np.arange(len(rec.cols))
ms = ST.measure_stream(rec, pos, p1["tot"], halves=True)
w2 = PM.windowed_stream(rec, pos, W=2)
print("halves stream", ms["M1_first_half"], ms["M1_second_half"]); print("windows W=2", w2["M1_w"])
Y = rec.counts(pos)
w8a = PM.windowed_from_counts(Y, W=8); w8b = PM.windowed_stream(rec, pos, W=8)
print("max diff counts vs stream", np.max(np.abs(np.array(w8a["M1_w"]) - np.array(w8b["M1_w"]))), w8a["P_share"], w8b["P_share"], w8a["P_amp"], w8b["P_amp"])
