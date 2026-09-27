import sys
from probs import *
from auto import AutoWrong
for name in sys.argv[1:]:
    sp = P[name]; bd = sp.board()
    an = run(sp, bd, sp.solver)
    A = AutoWrong(sp)
    wins = [m for m, v in an.items() if v[0] == 'W']
    rows = []
    for m, v in an.items():
        if v[0] == 'W' or m == 'pass': continue
        nb, nko = apply(bd, m, sp.solver)
        refs = A.refutations(nb, opp(sp.solver), nko)
        rows.append((m, len(refs), refs[0][1] if refs else '-'))
    rows.sort(key=lambda r: r[1])
    print(name, 'wins', wins, 'wrong(nrefs,bestkind):', rows[:8])
