"""Verdict table for cached run_same_worms results: one letter per pool (I inside, O outside,
T too typical), plus the pre-registered emulator rule."""
import sys, glob, pandas as pd
cache = sys.argv[1]
d = pd.concat([pd.read_csv(f) for f in glob.glob(f"{cache}/*.csv")])
REST = ['L1.distribution', 'L1.timescale', 'L2.correlation', 'L2.dimension', 'L4.leadlag', 'L4.dwell']
POKE = ['C1.pattern', 'C2.magnitude', 'P2.spread']
cols = REST + POKE + ['C3.kinetics']
d = d[d.metric.isin(cols)]
ab = {'inside': 'I', 'outside': 'O', 'too typical': 'T'}
d['v'] = d.verdict.map(lambda v: ab.get(v, '?'))
d = d.sort_values('fold')
t = d.pivot_table(index='system', columns='metric', values='v', aggfunc=lambda s: ''.join(s))[cols]
ok = lambda s: isinstance(s, str) and len(s) == 3 and s.count('I') >= 2
t['rest'] = t[REST].apply(lambda r: sum(ok(x) for x in r), axis=1)
t['poke'] = t[POKE].apply(lambda r: sum(ok(x) for x in r), axis=1)
t['EMU'] = (t.rest >= 5) & (t.poke == 3)
t.columns = [c.split('.')[-1][:6] for c in t.columns]
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(t.to_string())
