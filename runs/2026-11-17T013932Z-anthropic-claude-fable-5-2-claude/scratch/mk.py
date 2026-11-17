import sys, os; sys.path.insert(0,'scratch')
from build import *
from dr import tdump
from cands import C
import check_sgf
from make import show_sgf_board

def mk(name, slot=None, verbose=False, board=False):
    s=C[name]
    diag=s['diag'].replace('/','\n').replace(' ','')
    p=Problem(diag, defender='W', first=s['first'], maxnodes=s.get('maxnodes',10000000))
    root=parse_tree(s['tree']) if 'tree' in s else B2(p, **s.get('kw',{})).build()
    issues,notes=verify(p, root)
    sgf=to_sgf(p, root, make_tf(s.get('tf','id'), s.get('shift',(0,0))))
    if s.get('swap'): sgf=swap_colours(sgf)
    if verbose:
        print('=====', name); print(p.show(hgt=len(diag.split('\n')))); print('ROOT', p.report())
        print('\n'.join(tdump(root)))
        for x in notes: print('note:', x)
    for i in issues: print('ISSUE:', i)
    print('%s: nodes=%d maxdepth=%d issues=%d disagreements=%d'%(name, count_nodes(root), max_depth(root), len(issues), len(p.disagree)))
    for dg in p.disagree[:12]: print('   disagree:', ' '.join(dg[0]), '|', dg[1], dg[2])
    p.close()
    if issues: return None
    path='scratch/cands/%s.sgf'%name
    open(path,'w').write(sgf)
    errs,stats,nst=check_sgf.check(path)
    print('  ', stats, 'stones', nst, 'ERRS' if errs else 'ok', errs)
    if board: print(show_sgf_board(sgf))
    if slot:
        open('outputs/problem-%02d.sgf'%slot,'w').write(sgf)
        print('  -> slot', slot)
    return sgf

if __name__=='__main__':
    name=sys.argv[1]
    slot=int(sys.argv[2]) if len(sys.argv)>2 and sys.argv[2].isdigit() else None
    mk(name, slot, '-v' in sys.argv, '-b' in sys.argv)
