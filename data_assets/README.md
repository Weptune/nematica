# Bundled assets

## skuhersky2022_atlas.csv

Neuron soma positions (micrometres) for 300 *C. elegans* neurons from
Skuhersky et al. 2022, "Toward a more accurate 3D atlas of *C. elegans* neurons",
BMC Bioinformatics (CC BY 4.0), file `LowResAtlasWithHighResHeadsAndTails.csv` from
https://github.com/bluevex/elegans-atlas (the repository has no licence file; attribute the paper).
Not shipped in the public repository: run `python scripts/fetch_atlas.py` to download it
(checksum-verified against the version NEMATICA was tested with).

Columns, no header: name, anterior-posterior position (0 near I1L, about 795 at PLM),
dorsal-ventral (+ dorsal), left-right (+ left for most pairs). Six mid-body pairs have the
left-right sign flipped in this file (ALM, BDU, HSN, PDE, PVD, SDQ); `nematica.export.atlas`
corrects them. Provenance tag: [I] (atlas average, not the recorded animal's own positions).
