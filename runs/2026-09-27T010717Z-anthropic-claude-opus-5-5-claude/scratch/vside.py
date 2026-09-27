import json, glob, sys
from tl import *
from auto import show_tree
mind, maxd, lim = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
recs = [json.loads(l) for f in glob.glob('s2_*.jsonl') for l in open(f)]
recs = [r for r in recs if 'tdepth' in r and mind <= r['tdepth'] <= maxd and not r.get('toodeep')]
recs = [r for r in recs if min(ord(p[0]) for p in r['region']) > 97]
recs.sort(key=lambda r: (-len(r['region'])))
print(len(recs))
for n, r in enumerate(recs[:lim]):
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    sp = Spec(r['AB'], r['AW'], r['region'], 'B', 'live', [])
    print(f"#{n} {'B' if solver==1 else 'W'} to {r['goal']} tdepth={r['tdepth']} tnodes={r['tnodes']} key={r['key']} region={len(r['region'])}")
    print(show(sp.board(), set(s2i(p) for p in r['region']), {s2i(r['move']): '*'}))
    show_tree(r['tree'], 1, 'B' if solver == 1 else 'W')
