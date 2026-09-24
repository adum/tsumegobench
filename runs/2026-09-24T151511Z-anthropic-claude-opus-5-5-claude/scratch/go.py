import sys
sys.setrecursionlimit(10000)
N=19
def nb(p):
    x,y=p%N,p//N
    r=[]
    if x>0:r.append(p-1)
    if x<N-1:r.append(p+1)
    if y>0:r.append(p-N)
    if y<N-1:r.append(p+N)
    return r
NB=[nb(p) for p in range(N*N)]
def P(s): return (ord(s[1])-97)*N+(ord(s[0])-97)
def S(p): return chr(97+p%N)+chr(97+p//N)
def group(b,p):
    c=b[p];st=[p];g={p};libs=set()
    while st:
        q=st.pop()
        for r in NB[q]:
            if b[r]==0:libs.add(r)
            elif b[r]==c and r not in g:g.add(r);st.append(r)
    return g,libs
def play(b,p,c,ko=None):
    """returns (newboard,newko) or None if illegal"""
    if b[p]!=0 or p==ko:return None
    b=list(b);b[p]=c;o=3-c;cap=[]
    for r in NB[p]:
        if b[r]==o:
            g,l=group(b,r)
            if not l:
                for q in g:b[q]=0
                cap+=list(g)
    g,l=group(b,p)
    if not l:return None
    nk=None
    if len(cap)==1 and len(g)==1 and len(l)==1:nk=cap[0]
    return tuple(b),nk
def benson(b,c):
    """return set of points of c's unconditionally alive chains"""
    chains={};cid={}
    for p in range(N*N):
        if b[p]==c and p not in cid:
            g,l=group(b,p);i=len(chains);chains[i]=g
            for q in g:cid[q]=i
    regions=[];rid={}
    for p in range(N*N):
        if b[p]!=c and p not in rid:
            st=[p];g={p};rid[p]=len(regions)
            while st:
                q=st.pop()
                for r in NB[q]:
                    if b[r]!=c and r not in g:g.add(r);rid[r]=len(regions);st.append(r)
            regions.append(g)
    # region neighbors chains
    rch=[]
    for g in regions:
        s=set()
        for q in g:
            for r in NB[q]:
                if b[r]==c:s.add(cid[r])
        rch.append(s)
    # vital: every empty point in region adjacent to chain
    alive=set(chains);live_regions=set(range(len(regions)))
    def vital(ri,ci):
        for q in regions[ri]:
            if b[q]==0 and not any(cid.get(r)==ci for r in NB[q]):return False
        return True
    changed=True
    while changed:
        changed=False
        for ci in list(alive):
            v=sum(1 for ri in live_regions if ci in rch[ri] and rch[ri]<=alive and vital(ri,ci))
            if v<2:alive.discard(ci);changed=True
        for ri in list(live_regions):
            if not rch[ri]<=alive:live_regions.discard(ri);changed=True
    out=set()
    for ci in alive:out|=chains[ci]
    return out
def parse(diag):
    """diag: list of strings, top-left = sgf aa. X=black O=white . empty, other chars ignored as empty; '+' region marks? """
    b=[0]*(N*N)
    for y,row in enumerate(diag):
        for x,ch in enumerate(row.replace(' ','')):
            if ch=='X':b[y*N+x]=1
            elif ch=='O':b[y*N+x]=2
    return tuple(b)
class Solver:
    def __init__(s,region,attacker,keys):
        s.region=sorted(region);s.att=attacker;s.keys=keys;s.memo={};s.bmemo={}
    def status(s,b):
        d=3-s.att
        for k in s.keys:
            if b[k]!=d:return 1  # attacker won
        if b in s.bmemo:al=s.bmemo[b]
        else:al=s.bmemo[b]=all(k in benson(b,d) for k in s.keys)
        return -1 if al else 0
    def win(s,b,tm,ko,passes,depth):
        """True if attacker wins with tm to move within depth plies"""
        st=s.status(b)
        if st:return st==1
        if passes>=2 or depth==0:return False
        key=(b,tm,ko,passes,depth)
        if key in s.memo:return s.memo[key]
        att=(tm==s.att)
        res=not att
        for p in s.region+[None]:
            if p is None:nb_,nk=b,None
            else:
                r=play(b,p,tm,ko)
                if r is None:continue
                nb_,nk=r
            w=s.win(nb_,3-tm,nk,passes+1 if p is None else 0,depth-1)
            if att and w:res=True;break
            if not att and not w:res=False;break
        s.memo[key]=res
        return res
    def moves(s,b,tm,ko):
        out=[]
        for p in s.region:
            r=play(b,p,tm,ko)
            if r:out.append((p,r[0],r[1]))
        return out
    def dist(s,b,tm,ko,maxd=24):
        """attacker win distance, or None"""
        for d in range(0,maxd+1):
            if s.win(b,tm,ko,0,d):return d
        return None

class Solver2(Solver):
    """unlimited-depth boolean solver, memo w/o depth"""
    def win2(s,b,tm,ko,passes,depth=40):
        st=s.status(b)
        if st:return st==1
        if passes>=2 or depth==0:return False
        key=(b,tm,ko,passes)
        m=s.memo.get(key)
        if m is not None:return m
        att=(tm==s.att)
        res=not att
        cands=[]
        for p in s.region:
            r=play(b,p,tm,ko)
            if r is None:continue
            # prune defender filling own single eye
            if not att and all(b[q]==tm for q in NB[p]):continue
            cands.append(r)
        if not att or not cands: cands.append((b,None))  # pass
        else: cands.append((b,None))
        for nb_,nk in cands:
            ps=passes+1 if nb_ is b else 0
            w=s.win2(nb_,3-tm,nk,ps,depth-1)
            if att and w:res=True;break
            if not att and not w:res=False;break
        s.memo[key]=res
        return res
