import sys; sys.path.insert(0,'scratch')
from author import *
from specs import SPECS
n=sys.argv[1]
s=SPECS[int(n)] if n.isdigit() else dict(diag=n, first=sys.argv[2])
args=sys.argv[2:] if n.isdigit() else sys.argv[3:]
p=Problem(s['diag'].replace('/','\n'), defender='W', first=s['first'], maxnodes=10000000)
H=len(s['diag'].split('/'))
for a in args:
    seq=tuple(a.split(',')) if a!='-' else ()
    print('--- after', ' '.join(seq))
    print(p.show(seq, hgt=H))
    st,v=p.query(list(seq))
    if st: print(st); continue
    solver_to_move=len(seq)%2==0
    print('to move:', 'SOLVER' if solver_to_move else 'OPP', p.report(seq))
    if not solver_to_move:
        for r in sorted(v):
            if r=='pass': continue
            st2,v2=p.query(list(seq+(r,)))
            if st2: print('   ',r,st2); continue
            wins=[m for m,x in v2.items() if x>=2 and m!='pass']
            kos=[m for m,x in v2.items() if x==1 and m!='pass']
            print('   %s -> wins: %s%s%s'%(r,' '.join(sorted(wins)) or 'NONE', (' | ko: '+' '.join(kos)) if not wins else '', ' (tenuki ok)' if v2.get('pass',0)>=2 else ''))
    else:
        for m in sorted(v):
            if m=='pass' or v[m]>=2: continue
            st2,v2=p.query(list(seq+(m,)))
            if st2: continue
            refs=sorted(r for r,x in v2.items() if x<2 and r!='pass')
            print('   wrong %s (%s) refuted by: %s'%(m, {1:'ko',0:'x'}[v[m]], ' '.join(refs)))
p.close()
