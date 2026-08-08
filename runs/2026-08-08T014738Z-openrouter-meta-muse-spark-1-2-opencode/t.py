#!/usr/bin/env python3
import re

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
def to_sgf(x,y): return chr(97+x)+chr(97+y)
def neighbors(p):
    x,y=p
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny=x+dx,y+dy
        if 0<=nx<19 and 0<=ny<19:
            yield (nx,ny)
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
        print(f"  ZERO at {to_sgf(*z)} {b[z]}")
        return None
    print(f"  OK {len(ab)}B {len(aw)}W no zero lib")
    return b

def test_seq(ab,aw, seq):
    # seq = list of (color,coord)
    b=setup_ok(ab,aw)
    if b is None: return
    cur=b
    for c,coord in seq:
        cur2,err=apply(cur,c,coord)
        if err:
            print(f"   illegal {c}[{coord}]: {err}")
            return
        cur=cur2
        print(f"   {c}[{coord}] ok")
    # print board libs for color groups
    print("   final board groups:")
    seen=set()
    for p,col in cur.items():
        if p in seen: continue
        g,l=group_libs(cur,p)
        seen|=g
        if len(g)<6:
            print(f"     {col} group {','.join(to_sgf(*x) for x in g)} libs {len(l)} {','.join(to_sgf(*x) for x in list(l)[:6])}")

def show_board(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    # show region
    xs=[to_pos(s)[0] for s in ab+aw]
    ys=[to_pos(s)[1] for s in ab+aw]
    xmin=max(0,min(xs)-2); xmax=min(18, max(xs)+2)
    ymin=max(0,min(ys)-2); ymax=min(18, max(ys)+2)
    print(f" region x {xmin}-{xmax} y {ymin}-{ymax} (note y 0=top)")
    for y in range(ymin, ymax+1):
        row=""
        for x in range(xmin, xmax+1):
            if (x,y) in b: row+=b[(x,y)]
            else: row+="."
        print(f"{chr(97+y):>2} {row}  y={y}")
    print("   "+"".join(chr(97+x) for x in range(xmin,xmax+1)))

# Test P1 current attempt
print("P1 test current")
ab=["ij","jj","kj","lj","ik","jk","lk","il","kl"]
aw=["kk","mk","jm","lm","mm"]
show_board(ab,aw)
test_seq(ab,aw, [("B","km"),("W","km")])
test_seq(ab,aw, [("B","km")])
test_seq(ab,aw, [("B","jm"),("W","km")])
print()

# Try to design better P1: simple but not standard
# Let's try a center eye shape
print("Design P1 new idea: central B group with 1 eye, needs vital")
ab2=["hj","jj","kj","hk","jk","kk","hl","jl","kl"]
aw2=["ik","jk","kk"] # this overlaps - careful
# redo
ab2=["hj","jj","kj","hl","jl","kl","hk","kk"]
aw2=["ik","jk","lk","jj"]
# but need distinct
