import re

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
def to_sgf(x,y): return chr(97+x)+chr(97+y)
def neighbors(p):
    x,y=p
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny=x+dx,y+dy
        if 0<=nx<19 and 0<=ny<19: yield (nx,ny)
def group_libs(board, start):
    col=board[start]; vis=set([start]); stack=[start]; libs=set()
    while stack:
        cur=stack.pop()
        for nb in neighbors(cur):
            if nb not in board: libs.add(nb)
            elif board[nb]==col and nb not in vis:
                vis.add(nb); stack.append(nb)
    return vis, libs
def has_zero(board):
    seen=set()
    for p in board:
        if p in seen: continue
        g,l=group_libs(board,p); seen|=g
        if len(l)==0: return p
    return None
def apply(board,color,coord):
    p=to_pos(coord)
    if p in board: return None, f"occupied {coord}"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None, f"suicide {coord}"
    return nb, None
def setup_ok(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    z=has_zero(b)
    if z:
        print(f"ZERO {to_sgf(*z)} {b[z]}")
        return None
    return b

def test(ab,aw, lines):
    b=setup_ok(ab,aw)
    if not b: return
    for seq in lines:
        cur=b
        ok=True
        for col,coord in seq:
            nxt,err=apply(cur,col,coord)
            if err:
                print(f"FAIL {' '.join(c+'['+x+']' for c,x in seq)} -> {err}")
                ok=False; break
            cur=nxt
        if ok:
            print(f"OK {' '.join(c+'['+x+']' for c,x in seq)}")

# Try design P01 : center B to kill
# White group at jk/kk/lk with surrounding black
ab=["hk","ik","jk","hl","jl","kl","hj","jj","lj","mj","hm","jm","km"]
aw=["kk","lk","il","kl","jk"]  # overlap kl - fix
