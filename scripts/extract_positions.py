"""Extract tracked-neuron positions from the atlas archive (OSF e2syt, exported_data_full.tar.gz).

Streams the archive from stdin; for every pumpprobe recording, saves the median ZYX position (pixels;
z = slice index) of each reference neuron, i.e. each column of the recording's gcamp/labels, over
all volumes where it was matched (brains.json coordZYX + nInVolume, matches.txt), plus the manually
located targets. Local use only (third-party data stays in data/derived, gitignored).

Usage: cat exported_data_full.tar.gz | python -I scripts/extract_positions.py data/derived/positions
"""
import io, json, os, sys, tarfile
import numpy as np
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
want = ("brains.json", "matches.txt", "targets_manually_located.txt")
buf = {}
def reduce(d, files):
    b = json.loads(files["brains.json"])
    c = np.asarray(b["coordZYX"], dtype=float); n = np.asarray(b["nInVolume"], dtype=int)
    off = np.concatenate([[0], np.cumsum(n)[:-1]])
    M = np.loadtxt(io.BytesIO(files["matches.txt"]), comments="#", ndmin=2).astype(int)
    T, N = M.shape
    pos = np.full((N, 3), np.nan); cnt = np.zeros(N, int)
    for k in range(N):
        t = np.flatnonzero((M[:, k] >= 0) & (M[:, k] < n[:T]))
        if len(t):
            pts = c[off[t] + M[t, k]]
            pos[k] = np.median(pts, axis=0); cnt[k] = len(t)
    tg = [l.strip() for l in files.get("targets_manually_located.txt", b"").decode().splitlines() if l.strip() and not l.startswith("#")]
    tg = np.array([int(float(x)) for x in tg]) if tg else np.zeros(0, int)
    np.savez(os.path.join(out, d.replace("pumpprobe_", "") + ".npz"), pos=pos, count=cnt, targets=tg, n_volumes=T)
    print("saved", d, N, T, flush=True)
with tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz") as tf:
    for m in tf:
        base = os.path.basename(m.name); d = os.path.basename(os.path.dirname(m.name))
        if not d.startswith("pumpprobe_") or base not in want or not m.isfile():
            continue
        buf.setdefault(d, {})[base] = tf.extractfile(m).read()
        if all(w in buf[d] for w in want[:2]) and (len(buf[d]) == 3):
            try:
                reduce(d, buf.pop(d))
            except Exception as e:
                print("failed", d, repr(e), flush=True); buf.pop(d, None)
for d, f in buf.items():
    if "brains.json" in f and "matches.txt" in f:
        try: reduce(d, f)
        except Exception as e: print("failed", d, repr(e), flush=True)
    else:
        print("incomplete", d, list(f), flush=True)
