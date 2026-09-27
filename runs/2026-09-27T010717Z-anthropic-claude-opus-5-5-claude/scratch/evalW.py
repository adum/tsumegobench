import json, glob, sys
import tl
from tl import *
from mut import evaluate
tl.TIMEOUT = 20
part, nparts = int(sys.argv[1]), int(sys.argv[2])
recs = []
seen = set()
for f in sorted(glob.glob('s2_*.jsonl')) + sorted(glob.glob('seki_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        k = (tuple(sorted(r['AB'])), tuple(sorted(r['AW'])), r['goal'])
        if k in seen: continue
        seen.add(k); recs.append(r)
out = open(f'ew_{part}.jsonl', 'w')
for i, r in enumerate(recs):
    if i % nparts != part: continue
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    if solver != WHITE: continue
    sp = Spec(r['AB'], r['AW'], r['region'], 'W', r['goal'], r['key'], maxdepth=30)
    try: m = evaluate(sp)
    except Exception: m = None
    if m:
        out.write(json.dumps(dict(AB=r['AB'], AW=r['AW'], region=r['region'], key=r['key'], goal=r['goal'], solver=2, **m)) + '\n'); out.flush()
