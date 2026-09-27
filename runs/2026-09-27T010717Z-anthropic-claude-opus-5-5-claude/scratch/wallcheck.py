from probs import *
from registry import REG
for nn, (name, tf, T) in sorted(REG.items()):
    sp = tspec(P[name], T); bd = sp.board(); reg = set(sp.region)
    d = sp.solver if sp.goal == 'live' else opp(sp.solver)
    a = opp(d)
    seen = set(); weak = []
    for i in range(361):
        if i in seen or bd.b[i] == EMPTY: continue
        st, lb = bd.chain(i); seen.update(st)
        outside = [l for l in lb if l not in reg]
        inreg = any(s in reg for s in st)
        touches = any(q in reg for s in st for q in NEI[s])
        if touches and len(outside) <= 2:
            weak.append(('att' if bd.b[i] == a else 'DEF', [i2s(s) for s in st], 'outside libs', [i2s(l) for l in outside], 'in-region libs', len(lb) - len(outside)))
    print(nn, name, weak)
