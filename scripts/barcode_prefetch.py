"""Study 4: cache the repeated and unique flicker spikes for every session (caching only). Resumable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nematica.barcode import data as BD  # noqa: E402

for a in BD.sessions():
    sess = a["path"].split("/")[0]
    try:
        z = BD.cache(a)
        print(sess, "cached", len(z["starts"]), "repeats", len(z["units"]), "units", flush=True)
    except Exception as e:  # noqa: BLE001
        print(sess, "error", type(e).__name__, e, flush=True)
