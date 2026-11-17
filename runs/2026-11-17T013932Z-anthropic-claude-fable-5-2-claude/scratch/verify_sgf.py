"""End-to-end check: read each output SGF, rebuild the solver model in final board coordinates,
and verify every branch (RIGHT leaves win, wrong lines are refuted, no winning alternative missing)."""
import sys, re; sys.path.insert(0,'scratch')
from author import *
from cands import C, FINAL
import check_sgf

def model(name):
    s=C[name]; diag=s['diag'].replace('/','\n')
    base=Problem(diag, defender='W', first=s['first'])
    tf=make_tf(s.get('tf','id'), s.get('shift',(0,0)))
    swap=s.get('swap',False)
    p=Problem.__new__(Problem)
    p.defender='B' if swap else 'W'; p.attacker='W' if swap else 'B'
    fc=s['first']
    if swap: fc='B' if fc=='W' else 'W'
    p.first=fc
    bl=[tf(q) for q in base.black]; wh=[tf(q) for q in base.white]
    p.black, p.white = (wh, bl) if swap else (bl, wh)
    p.regboth=[tf(q) for q in base.regboth]; p.regatt=[tf(q) for q in base.regatt]; p.target=[tf(q) for q in base.target]
    p.rows=['.'*19]*19; p.maxnodes=20000000
    p.seeds=[None]; p.procs={}; p.cache={}; p.disagree=[]
    return p

def to_nodes(nodes, kids):
    """convert check_sgf parse output to Node chain; returns list of top Node(s)"""
    head=None; cur=None
    for nd in nodes:
        col='B' if 'B' in nd else 'W'
        n=Node(nd[col][0]); n.auto=False
        if 'RIGHT' in ''.join(nd.get('C',[])): n.right=True
        if head is None: head=n
        else: cur.add(n)
        cur=n
    tops=[]
    for kn,kk in kids:
        tops.extend(to_nodes(kn,kk))
    if head is None: return tops
    for t in tops: cur.add(t)
    return [head]

ok=True
for slot,name in sorted(FINAL.items()):
    path='outputs/problem-%02d.sgf'%slot
    txt=open(path).read()
    nodes,kids=check_sgf.parse(txt)
    rootprops=nodes[0]
    p=model(name)
    assert sorted(rootprops['AB'])==sorted(p.black) and sorted(rootprops['AW'])==sorted(p.white), 'setup mismatch '+name
    root=Node()
    for t in to_nodes(nodes[1:],kids): root.add(t)
    issues,notes=verify(p, root)
    errs,stats,nst=check_sgf.check(path)
    st,v=p.query([])
    wins=[m for m,x in v.items() if x==2 and m!='pass']
    print('%02d %-7s first=%s wins=%s nodes=%d maxlen=%d right=%d stones=%d issues=%d fmt=%s'%(slot,name,p.first,wins,stats['nodes'],stats['maxlen'],stats['right'],nst,len(issues),'ok' if not errs else errs))
    for i in issues: print('   ISSUE', i); ok=False
    if errs: ok=False
    p.close()
print('ALL OK' if ok else 'PROBLEMS FOUND')
