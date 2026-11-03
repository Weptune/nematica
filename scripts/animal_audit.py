"""Look inside the two animal datasets before writing anything that analyses them.

Run on a machine with internet (the same one running the human download):

    python scripts/animal_audit.py

What it does, without keeping any large file:
  1. Mouse barrel cortex (Dalgleish et al. 2020, figshare 13128950, MIT):
     asks figshare for the file list, downloads the SMALLEST session zip
     (about 0.4 GB), lists everything inside it, and describes every .mat /
     .npy file (variable names, shapes). The zip is deleted afterwards
     (it is a file this script downloaded itself, into its own temp folder).
  2. Mouse hippocampus (Bocchio, Vorobyev et al., Zenodo 11500028, CC BY 4.0):
     streams the start of the single 18.5 GB archive and lists the files it
     contains, stopping after --zenodo-gb gigabytes have been read. Small text
     files (readme, csv, json, yaml under 2 MB) are saved for reading.

Everything it learns goes to data/raw/animal_audit/ (gitignored, local only):
  audit.txt            the listing and variable descriptions
  zenodo_small/...     small text files found in the archive

Nothing here is redistributed. Send back audit.txt (it holds only names,
shapes and sizes) and the analysis scripts can be written against it.
"""
import argparse
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "animal_audit")
FIGSHARE_API = "https://api.figshare.com/v2/articles/13128950"
ZENODO_URL = "https://zenodo.org/records/11500028/files/all-optical.tar.gz?download=1"
UA = {"User-Agent": "nematica-audit/1.0"}
TEXT_EXT = (".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".tsv", ".ini", ".cfg", ".py", ".m")

log_lines = []


def log(msg=""):
    print(msg, flush=True)
    log_lines.append(msg)


def save_log():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "audit.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")


def gb(n):
    return f"{n / 1e9:.2f} GB"


def describe_array_file(path, label):
    """Print variable names and shapes of a .mat or .npy file."""
    low = path.lower()
    try:
        if low.endswith(".npy"):
            import numpy as np
            a = np.load(path, allow_pickle=False, mmap_mode="r")
            log(f"    {label}: npy {a.dtype} {a.shape}")
            return
        if low.endswith(".mat"):
            try:
                from scipy.io import whosmat
                for name, shape, cls in whosmat(path):
                    log(f"    {label}: {name} {cls} {shape}")
                return
            except NotImplementedError:
                pass  # MATLAB v7.3 = HDF5
            except ValueError:
                pass
            import h5py

            def walk(g, prefix):
                for k in g.keys():
                    item = g[k]
                    if hasattr(item, "shape"):
                        log(f"    {label}: {prefix}{k} {item.dtype} {item.shape}")
                    else:
                        walk(item, prefix + k + "/")
            with h5py.File(path, "r") as f:
                walk(f, "")
    except Exception as e:  # keep going; the listing is what matters
        log(f"    {label}: could not read ({type(e).__name__}: {e})")


def describe_npy_object(path, label):
    """Suite2p stat.npy / ops.npy are pickled object arrays: report keys only."""
    try:
        import numpy as np
        a = np.load(path, allow_pickle=True)
        if a.dtype == object:
            first = a.flat[0] if a.size else None
            if isinstance(first, dict):
                log(f"    {label}: object array {a.shape}, first item keys: {sorted(first.keys())[:40]}")
            else:
                log(f"    {label}: object array {a.shape}, item type {type(first).__name__}")
        else:
            log(f"    {label}: npy {a.dtype} {a.shape}")
    except Exception as e:
        log(f"    {label}: could not read ({type(e).__name__}: {e})")


def download(url, dest, retries=5):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as fh:
                total = int(r.headers.get("Content-Length") or 0)
                got, t0, last = 0, time.time(), 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
                    if time.time() - last > 15:
                        last = time.time()
                        rate = got / max(1e-6, last - t0) / 1e6
                        print(f"      {gb(got)} of {gb(total)} ({rate:.1f} MB/s)", flush=True)
            return
        except Exception as e:
            log(f"    download attempt {attempt} failed: {e}")
            time.sleep(10 * attempt)
    raise RuntimeError(f"could not download {url}")


def audit_figshare(min_free_gb):
    log("=" * 70)
    log("MOUSE BARREL CORTEX: Dalgleish et al. 2020, figshare 13128950")
    log("=" * 70)
    req = urllib.request.Request(FIGSHARE_API, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        meta = json.load(r)
    files = meta.get("files", [])
    log(f"title: {meta.get('title')}")
    log(f"license: {(meta.get('license') or {}).get('name')}")
    log(f"{len(files)} files, {gb(sum(f['size'] for f in files))} in total:")
    for f in sorted(files, key=lambda f: f["name"]):
        log(f"  {f['name']}  {gb(f['size'])}")
    desc = meta.get("description") or ""
    log("description (as given by the authors):")
    log("  " + desc.replace("\n", "\n  ")[:4000])

    zips = [f for f in files if f["name"].lower().endswith(".zip")]
    if not zips:
        log("no zip files found; stopping this part")
        return
    pick = min(zips, key=lambda f: f["size"])
    free = shutil.disk_usage(ROOT).free / 1e9
    if free - pick["size"] / 1e9 * 2.2 < min_free_gb:
        log(f"not enough free disk to unpack {pick['name']} (free {free:.1f} GB); skipping")
        return
    log("")
    log(f"downloading the smallest session: {pick['name']} ({gb(pick['size'])})")
    tmp = tempfile.mkdtemp(prefix="nematica_audit_")
    try:
        zpath = os.path.join(tmp, "session.zip")
        download(pick["download_url"], zpath)
        with zipfile.ZipFile(zpath) as z:
            infos = z.infolist()
            log(f"{len(infos)} entries inside:")
            for i in infos:
                log(f"  {i.filename}  {i.file_size / 1e6:.1f} MB")
            log("")
            log("variables inside data files:")
            unpack = os.path.join(tmp, "x")
            for i in infos:
                low = i.filename.lower()
                if i.is_dir() or not low.endswith((".mat", ".npy")):
                    continue
                p = z.extract(i, unpack)
                base = os.path.basename(low)
                if low.endswith(".npy") and base in ("stat.npy", "ops.npy"):
                    describe_npy_object(p, i.filename)
                else:
                    describe_array_file(p, i.filename)
                os.remove(p)
            for i in infos:
                if i.filename.lower().endswith(TEXT_EXT) and i.file_size < 2e6:
                    log(f"--- text file {i.filename} ---")
                    log(z.read(i).decode("utf-8", "replace")[:3000])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    save_log()


def audit_zenodo(max_gb):
    log("")
    log("=" * 70)
    log("MOUSE HIPPOCAMPUS: Bocchio, Vorobyev et al., Zenodo 11500028")
    log("=" * 70)
    small_dir = os.path.join(OUT, "zenodo_small")
    os.makedirs(small_dir, exist_ok=True)
    req = urllib.request.Request(ZENODO_URL, headers=UA)
    r = urllib.request.urlopen(req, timeout=120)
    total = int(r.headers.get("Content-Length") or 0)
    log(f"archive size: {gb(total)}; reading at most {max_gb} GB of it")

    class Counting(io.RawIOBase):
        def __init__(self, raw):
            self.raw, self.n = raw, 0

        def readable(self):
            return True

        def readinto(self, b):
            if self.n > max_gb * 1e9:
                return 0
            data = self.raw.read(len(b))
            self.n += len(data)
            b[: len(data)] = data
            return len(data)

    src = Counting(r)
    n, by_ext, last = 0, {}, time.time()
    try:
        with tarfile.open(fileobj=io.BufferedReader(src, 1 << 20), mode="r|gz") as tar:
            for m in tar:
                n += 1
                ext = os.path.splitext(m.name)[1].lower() or "(none)"
                c = by_ext.setdefault(ext, [0, 0])
                c[0] += 1
                c[1] += m.size
                log(f"  {m.name}  {m.size / 1e6:.1f} MB")
                if m.isfile() and m.name.lower().endswith(TEXT_EXT) and m.size < 2e6:
                    fh = tar.extractfile(m)
                    if fh:
                        safe = m.name.replace("/", "__").replace("\\", "__").lstrip(".")
                        with open(os.path.join(small_dir, safe), "wb") as out:
                            out.write(fh.read())
                if time.time() - last > 30:
                    last = time.time()
                    print(f"      read {gb(src.n)} compressed so far", flush=True)
                    save_log()
    except (tarfile.ReadError, EOFError, OSError) as e:
        log(f"(stopped after {gb(src.n)}: {type(e).__name__})")
    log("")
    log(f"{n} entries seen in the first {gb(src.n)} of {gb(total)}")
    for ext, (k, s) in sorted(by_ext.items(), key=lambda kv: -kv[1][1]):
        log(f"  {ext}: {k} files, {gb(s)}")
    save_log()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zenodo-gb", type=float, default=3.0,
                    help="how much of the 18.5 GB hippocampus archive to stream (default 3)")
    ap.add_argument("--min-free-gb", type=float, default=5.0)
    ap.add_argument("--skip-figshare", action="store_true")
    ap.add_argument("--skip-zenodo", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if not args.skip_figshare:
        try:
            audit_figshare(args.min_free_gb)
        except Exception as e:
            log(f"barrel cortex audit failed: {type(e).__name__}: {e}")
    if not args.skip_zenodo:
        try:
            audit_zenodo(args.zenodo_gb)
        except Exception as e:
            log(f"hippocampus audit failed: {type(e).__name__}: {e}")
    save_log()
    log(f"\nwritten: {os.path.join(OUT, 'audit.txt')}")


if __name__ == "__main__":
    sys.exit(main())
