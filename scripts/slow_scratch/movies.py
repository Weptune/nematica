import sys, json; sys.path.insert(0,'/home/claude/nematica')
from nematica.map import data
import h5py, numpy as np
out={}
for ds in ("000021","000022"):
    for a in sorted([a for a in data.dandi_assets(ds) if "probe" not in a["path"]], key=lambda a:a["path"]):
        uid=a["path"].split("/")[0]
        try:
            h=h5py.File(data.open_url(f"{data.DANDI}/assets/{a['asset_id']}/download/"),"r")
            r={"dandiset":ds}
            for k in h["intervals"].keys():
                if "natural_movie" in k:
                    g=h["intervals"][k]; st=g["start_time"][:]; en=g["stop_time"][:]
                    fr=g["frame"][:] if "frame" in g else None
                    rep=int((np.asarray(fr)==0).sum()) if fr is not None else None
                    nfr=int(np.max(fr))+1 if fr is not None else None
                    blocks=np.split(st, np.flatnonzero(np.diff(st)>1.0)+1)
                    r[k]={"n_presentations":int(len(st)),"repeats":rep,"frames_per_repeat":nfr,
                          "frame_s":float(np.median(en-st)),"blocks":[[float(b[0]),float(b[-1])] for b in blocks]}
            out[uid]=r; print(uid, {k:(v["repeats"],v["frames_per_repeat"],round(v["frame_s"],4),len(v["blocks"])) for k,v in r.items() if k!="dandiset"}, flush=True)
        except Exception as e:
            out[uid]={"error":repr(e)}; print(uid,"ERR",e,flush=True)
json.dump(out,open("movie_meta.json","w"),indent=1)
