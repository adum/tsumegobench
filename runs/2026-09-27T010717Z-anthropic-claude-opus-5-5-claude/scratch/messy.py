import json, glob, sys
from tl import *
from auto import show_tree
recs = [json.loads(l) for f in glob.glob('s2_*.jsonl') for l in open(f)]
recs = [r for r in recs if 'tdepth' in r and r['tdepth'] <= 3 and not r.get('toodeep')]
out = []
for r in recs:
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    sp = Spec(r['AB'], r['AW'], r['region'], 'B', 'live', [])
    bd = sp.board()
    reg = set(s2i(p) for p in r['region'])
    # count attacker stones inside region (intruders), and stones of both colors near key move
    att = 3 - r['defcolor']
    intr = sum(1 for p in reg if bd.b[p] == att)
    k = s2i(r['move']); kx, ky = k % 19, k // 19
    near = set()
    for i in range(361):
        if bd.b[i] and abs(i % 19 - kx) <= 2 and abs(i // 19 - ky) <= 2:
            near.add(bd.b[i])
    if intr >= 1 and len(near) == 2:
        out.append((intr, r))
out.sort(key=lambda x: -x[0])
print(len(out))
json.dump([r for i, r in out], open('messy_list.json', 'w'))
for n, (intr, r) in enumerate(out[:int(sys.argv[1])]):
    solver = r['defcolor'] if r['goal'] == 'live' else 3 - r['defcolor']
    sp = Spec(r['AB'], r['AW'], r['region'], 'B', 'live', [])
    side = 'side' if min(ord(p[0]) for p in r['region']) > 97 else 'corner'
    print(f"#{n} {side} {'BW'[solver-1]} to {r['goal']} tdepth={r['tdepth']} intruders={intr} key={r['key']}")
    print(show(sp.board(), set(s2i(p) for p in r['region']), {s2i(r['move']): '*'}))
    show_tree(r['tree'], 1, 'BW'[solver-1])
