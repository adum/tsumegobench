import json, glob, sys
from tl import *
recs = [json.loads(l) for f in glob.glob(sys.argv[1]) for l in open(f)]
recs = [r for r in recs if 'tdepth' in r and not r.get('toodeep')]
def mainline(t):
    out = []
    while isinstance(t, list) and t:
        m, s = t[0]; out.append(m); t = s
    return out
rows = []
for i, r in enumerate(recs):
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    side = 'side' if min(ord(p[0]) for p in r['region']) > 97 else 'corner'
    rows.append((r['tdepth'], r['tnodes'], side, 'BW'[solver-1], r['goal'], len(r['region']), ' '.join(mainline(r['tree'])), i))
rows.sort(key=lambda x: (-x[0], x[1]))
for row in rows[:int(sys.argv[2])]: print(row)
