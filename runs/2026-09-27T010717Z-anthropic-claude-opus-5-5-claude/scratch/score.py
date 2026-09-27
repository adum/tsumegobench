import json, glob, sys, time
import tl
from tl import *
from auto import *
tl.TIMEOUT = 30
files = sys.argv[1]; out = open(sys.argv[2], 'w')
part, nparts = int(sys.argv[3]), int(sys.argv[4])
seen = set(); recs = []
for f in sorted(glob.glob(files)):
    for line in open(f):
        r = json.loads(line)
        k = (tuple(sorted(r['AB'])), tuple(sorted(r['AW'])), r['goal'])
        if k in seen: continue
        seen.add(k); recs.append(r)
def depth(t):
    if isinstance(t, str): return 0
    return max(1 + depth(s) for m, s in t)
for i, r in enumerate(recs):
    if i % nparts != part: continue
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    sp = Spec(r['AB'], r['AW'], r['region'], 'B' if solver == 1 else 'W', r['goal'], r['key'], maxdepth=30)
    try:
        A = Auto(sp, 3, maxply=13)
        t = A.build_right(sp.board(), sp.solver, -1, 0, [])
        r['tdepth'] = depth(t); r['tnodes'] = count(t)
        s = json.dumps(t)
        r['tree'] = t
        r['toodeep'] = 'TOO_DEEP' in s
    except Exception as e:
        r['err'] = str(e)
    out.write(json.dumps(r) + '\n'); out.flush()
