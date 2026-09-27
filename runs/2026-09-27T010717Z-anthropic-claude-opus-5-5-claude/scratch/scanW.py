import json, glob, sys
import tl
from tl import *
from auto import AutoWrong
tl.TIMEOUT = 30
recs = []
for f in glob.glob('g4_*.jsonl') + glob.glob('ew_*.jsonl'):
    for l in open(f):
        r = json.loads(l)
        if r['solver'] == WHITE and r['L'] >= 1: recs.append(r)
seen = set(); out = []
for r in recs:
    k = (tuple(sorted(r['AB'])), tuple(sorted(r['AW'])))
    if k in seen: continue
    seen.add(k)
    sp = Spec(r['AB'], r['AW'], r['region'], 'W', r['goal'], r['key'])
    bd = sp.board()
    an = run(sp, bd, WHITE)
    A = AutoWrong(sp)
    kos = 0; rows = []
    for m, v in an.items():
        if v[0] == 'W' or m == 'pass': continue
        nb, nko = apply(bd, m, WHITE)
        refs = A.refutations(nb, BLACK, nko)
        rows.append((len(refs), m, refs[0][1]))
    rows.sort()
    top = rows[:5]
    kos = sum(1 for t in top if t[2] != 'clean')
    r['kos'] = kos; r['top'] = top
    out.append(r)
    print(r['line'][0], r['goal'], 'L', r['L'], 'tempt', r['tempt'], 'kos', kos, flush=True)
json.dump(out, open('scanW.json', 'w'))
