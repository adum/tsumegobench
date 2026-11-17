"""Independent SGF validator: structure, legality, alternation, limits."""
import sys, re
sys.path.insert(0,'scratch')
from tsu import play, pt, xy

def parse(s):
    pos=0
    def skip():
        nonlocal pos
        while pos<len(s) and s[pos].isspace(): pos+=1
    def node():
        nonlocal pos
        props={}
        skip()
        while pos<len(s) and s[pos] not in ';()':
            m=re.match(r'[A-Z]+', s[pos:])
            assert m, 'bad prop at %d: %r'%(pos,s[pos:pos+10])
            k=m.group(0); pos+=len(k); vals=[]
            skip()
            while pos<len(s) and s[pos]=='[':
                e=pos+1
                while s[e]!=']':
                    if s[e]=='\\': e+=1
                    e+=1
                vals.append(s[pos+1:e]); pos=e+1; skip()
            props.setdefault(k,[]).extend(vals)
        return props
    def tree():
        nonlocal pos
        skip(); assert s[pos]=='(' ; pos+=1
        nodes=[]; kids=[]
        skip()
        while s[pos]==';':
            pos+=1; nodes.append(node()); skip()
        while s[pos]=='(':
            kids.append(tree()); skip()
        assert s[pos]==')'; pos+=1
        return nodes,kids
    t=tree(); skip(); assert pos==len(s), 'trailing data'
    return t

def check(path):
    s=open(path).read()
    errs=[]
    assert s.startswith('(;') and s.rstrip().endswith(')')
    nodes,kids=parse(s)
    root=nodes[0]
    if root.get('SZ')!=['19']: errs.append('SZ')
    if 'AB' not in root or 'AW' not in root: errs.append('AB/AW')
    if 'C' in root or 'B' in root or 'W' in root: errs.append('root has move/comment')
    board={}
    for p in root['AB']:
        if p in board: errs.append('dup setup '+p)
        board[p]='X'
    for p in root['AW']:
        if p in board: errs.append('dup setup '+p)
        board[p]='O'
    stats=dict(nodes=0, maxlen=0, right=0, leaves=0, firsts=set())
    def walk(nodes, kids, board, last, depth, ko):
        for i,nd in enumerate(nodes):
            mv=[k for k in ('B','W') if k in nd]
            if len(mv)!=1 or len(nd[mv[0]])!=1: errs.append('node without exactly one move'); return
            col=mv[0]; p=nd[col][0]
            if len(p)!=2: errs.append('pass/bad move'); return
            if last and col==last: errs.append('colour not alternating at depth %d'%depth)
            if depth==0: stats['firsts'].add(col)
            x,y=xy(p)
            if not (0<=x<19 and 0<=y<19): errs.append('off board')
            board=dict(board)
            try:
                caps=play(board,p,'X' if col=='B' else 'O')
            except ValueError as e:
                errs.append('illegal %s at depth %d'%(e,depth)); return
            if ko and p==ko: errs.append('ko violation %s'%p)
            ko=caps[0] if len(caps)==1 else None
            # ko only if capturing stone is single with one liberty
            if ko:
                from tsu import group
                g,l=group(board,p)
                if len(g)!=1 or len(l)!=1: ko=None
            stats['nodes']+=1; depth+=1; last=col
            stats['maxlen']=max(stats['maxlen'],depth)
            for k in nd:
                if k not in ('B','W','C','LB','TR','MA'): errs.append('odd prop '+k)
            isleaf=(i==len(nodes)-1 and not kids)
            c=''.join(nd.get('C',[]))
            if 'RIGHT' in c:
                stats['right']+=1
                if not isleaf: errs.append('RIGHT on non-leaf')
                if col not in stats['firsts']: errs.append('RIGHT on opponent move')
            if isleaf:
                stats['leaves']+=1
                if 'RIGHT' not in c and col in stats['firsts'] and len(stats['firsts'])==1:
                    errs.append('wrong leaf ends on solver move at depth %d (%s)'%(depth,p))
        for kn,kk in kids:
            walk(kn,kk,board,last,depth,ko)
    walk(nodes[1:],kids,board,None,0,None)
    if len(stats['firsts'])!=1: errs.append('first colour inconsistent')
    if stats['nodes']>120: errs.append('too many nodes')
    if stats['maxlen']>14: errs.append('line too long')
    if stats['right']<1: errs.append('no RIGHT')
    return errs, stats, len(root['AB'])+len(root['AW'])

if __name__=='__main__':
    for path in sys.argv[1:]:
        errs,stats,nst=check(path)
        print(path, 'OK' if not errs else 'ERRORS', stats, 'stones', nst)
        for e in errs: print('   ', e)
