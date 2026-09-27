import json, glob, sys
from tl import *
kind = sys.argv[1]; goal = sys.argv[5] if len(sys.argv)>5 else None; mind = int(sys.argv[2]); maxd = int(sys.argv[3]); lim = int(sys.argv[4]) if len(sys.argv)>4 else 30
seen = set(); recs = []
for f in glob.glob(kind):
    for line in open(f):
        r = json.loads(line)
        k = (tuple(sorted(r['AB'])), tuple(sorted(r['AW'])), r['goal'])
        if k in seen: continue
        seen.add(k); recs.append(r)
recs = [r for r in recs if mind <= r['depth'] <= maxd and (goal is None or r['goal']==goal)]
recs.sort(key=lambda r: -r['depth'])
print(len(recs))
for n, r in enumerate(recs[:lim]):
    sp = Spec(r['AB'], r['AW'], r['region'], 'B', 'live', [])
    solver = r['defcolor'] if r['goal']=='live' else 3-r['defcolor']
    print(f"#{n} {'B' if solver==1 else 'W'} to {r['goal']} move={r['move']} depth={r['depth']} near={r.get('nearmiss')} nstones={len(r['AB'])+len(r['AW'])}")
    print(show(sp.board(), set(s2i(p) for p in r['region']), {s2i(r['move']):'*'}))
