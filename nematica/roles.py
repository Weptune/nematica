"""Primary role of each C. elegans neuron class recorded in the atlas, as NEMATICA names classes
(`nematica.data.pumpprobe.neuron_class`). Written 6 Nov 2026, before the role-split test was run.

Roles follow the WormAtlas individual-neuron descriptions (White et al. 1986; Altun and Hall,
WormAtlas). A class whose description gives two roles (for example sensory and motor, or
interneuron and motor) is "mixed" and left out of the primary comparison; the sensitivity
analysis puts each mixed class in its first-listed role (MIXED_FIRST). The pharyngeal nervous
system is its own group: it is joined to the rest of the brain by one pair of neurons (RIP).

Atlas labels that are not neuron classes (glia such as AMSO, uncertain names with "?",
annotation leftovers such as TARGET or MERGE, numbers) have no entry and are excluded.
"""

SENSORY = {
    "ADE", "ADF", "ADL", "AFD", "AQR", "ASE", "ASG", "ASH", "ASI", "ASJ", "ASK", "AWA", "AWB",
    "AWC", "AWCOFF", "AWCON", "BAG", "CEP", "FLP", "IL2", "IL02", "OLL", "OLQ", "PHA", "PHB",
    "PHC", "PLM", "PQR", "PVM", "URX", "URY",
}
INTER = {
    "ADA", "AIA", "AIB", "AIM", "AIN", "AIY", "AIZ", "AJV", "ALA", "AUA", "AVA", "AVB", "AVD",
    "AVE", "AVF", "AVG", "AVH", "AVJ", "AVK", "DVC", "LUA", "PVC", "PVQ", "PVW", "RIA", "RIB",
    "RIC", "RIF", "RIG", "RIH", "RIP", "RIR", "RIS", "RMG", "SAA",
}
MOTOR = {
    "AS01", "DA01", "DB", "DB01", "DB02", "DD01", "DVB", "RIV", "RMD", "RME", "RMF", "RMH",
    "SAB", "SABD", "SABV", "SMB", "SMD", "URA", "VA01", "VB01", "VB02", "VD", "VD01", "VD02",
}
PHARYNX = {"I1", "I2", "I3", "I4", "I5", "I6", "M1", "M2", "M3", "M4", "M5", "MC", "MI", "NSM"}
# two roles in WormAtlas; the first-listed role is used only in the sensitivity analysis
MIXED_FIRST = {
    "IL1": "sensory", "IL01": "sensory", "URB": "sensory", "ALN": "sensory", "DVA": "inter",
    "RIM": "inter", "RID": "motor", "SIA": "inter", "SIB": "inter", "AVL": "inter",
    "PVN": "inter",
}

ROLE = {**{c: "sensory" for c in SENSORY}, **{c: "inter" for c in INTER},
        **{c: "motor" for c in MOTOR}, **{c: "pharynx" for c in PHARYNX},
        **{c: "mixed" for c in MIXED_FIRST}}


def role(cls: str, mixed_as_first: bool = False) -> str | None:
    """Role of a class, or None if the label is not a neuron class."""
    r = ROLE.get(cls)
    if r == "mixed" and mixed_as_first:
        return MIXED_FIRST[cls]
    return r
