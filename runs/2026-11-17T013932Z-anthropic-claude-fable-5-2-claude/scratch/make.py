import sys, os; sys.path.insert(0,'scratch')
from build import *
from dr import tdump
from problems import PROBLEMS
import check_sgf

def show_sgf_board(sgf):
    import re
    ab=re.search(r'AB((?:\[\w\w\])+)',sgf).group(1); aw=re.search(r'AW((?:\[\w\w\])+)',sgf).group(1)
    g={}
    for p in re.findall(r'\[(\w\w)\]',ab): g[p]='X'
    for p in re.findall(r'\[(\w\w)\]',aw): g[p]='O'
    out=['   '+' '.join('abcdefghijklmnopqrs')]
    for y in range(19):
        out.append(' %s '%chr(97+y)+' '.join(g.get(pt(x,y),'.') for x in range(19)))
    return '\n'.join(out)

def make(n, write=True, verbose=True):
    s=PROBLEMS[n]
    diag=s['diag'].replace('/','\n').replace(' ','')
    p=Problem(diag, defender='W', first=s['first'], maxnodes=s.get('maxnodes',10000000))
    if 'tree' in s:
        root=parse_tree(s['tree'])
    else:
        root=B2(p, **s.get('kw',{})).build()
    issues,notes=verify(p, root)
    sgf=to_sgf(p, root, make_tf(s.get('tf','id'), s.get('shift',(0,0))))
    if s.get('swap'): sgf=swap_colours(sgf)
    if verbose:
        print('=====', n); print(p.show()); print('ROOT', p.report())
        print('\n'.join(tdump(root)))
        for x in notes: print('note:', x)
    for i in issues: print('ISSUE:', i)
    print('problem %d: nodes=%d maxdepth=%d issues=%d'%(n, count_nodes(root), max_depth(root), len(issues)))
    p.close()
    if write and not issues:
        path='outputs/problem-%02d.sgf'%n
        open(path,'w').write(sgf)
        errs,stats,nst=check_sgf.check(path)
        print('  wrote', path, stats, 'stones', nst, 'ERRS' if errs else 'ok', errs)
        if verbose: print(show_sgf_board(sgf))
    return sgf

if __name__=='__main__':
    ns=[int(a) for a in sys.argv[1].split(',')]
    write='-n' not in sys.argv
    verbose='-q' not in sys.argv
    for n in ns: make(n, write, verbose)
