import json, glob, sys
from tl import *
from auto import show_tree
mind = int(sys.argv[1]); maxd = int(sys.argv[2]); lim = int(sys.argv[3]); filt = sys.argv[4] if len(sys.argv) > 4 else ''
recs = [json.loads(l) for f in glob.glob(sys.argv[5] if len(sys.argv)>5 else 's2_*.jsonl') for l in open(f)]
recs = [r for r in recs if 'tdepth' in r and mind <= r['tdepth'] <= maxd and not r.get('toodeep')]
if 'live' in filt: recs = [r for r in recs if r['goal'] == 'live']
if 'kill' in filt: recs = [r for r in recs if r['goal'] == 'kill']
recs.sort(key=lambda r: (-r['tdepth'], r['tnodes']))
print(len(recs))
for n, r in enumerate(recs[:lim]):
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    sp = Spec(r['AB'], r['AW'], r['region'], 'B', 'live', [])
    print(f"#{n} {'B' if solver==1 else 'W'} to {r['goal']} tdepth={r['tdepth']} tnodes={r['tnodes']} key={r['key']}")
    print(show(sp.board(), set(s2i(p) for p in r['region']), {s2i(r['move']): '*'}))
    show_tree(r['tree'], 1, 'B' if solver == 1 else 'W')
