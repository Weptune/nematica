"""Study 3: download and cache NM3 spikes for every session that has NM3 (from feasibility F1). Caching
only; no statistic of the activity is computed. Resumable (cached sessions are skipped)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nematica.persist import data as PD  # noqa: E402
from nematica.slow import data as sd  # noqa: E402


def main():
    feas = {r["session"]: r for r in json.loads((ROOT / "docs/figures/persist/feasibility.json").read_text())}
    for ds, a in sd.sessions():
        sess = a["path"].split("/")[0]
        if not feas.get(sess, {}).get("nm3_complete"):
            continue
        try:
            z = PD.nm3_cache(a)
            print(sess, "cached", int(len(z["starts"])), "repeats", int(len(z["units"])), "units", flush=True)
        except Exception as e:  # noqa: BLE001
            print(sess, "error", type(e).__name__, e, flush=True)


if __name__ == "__main__":
    main()
