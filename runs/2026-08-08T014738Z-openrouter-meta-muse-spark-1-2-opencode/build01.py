import pathlib, re, itertools, json, random

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
def to_sgf(x,y): return chr(97+x)+chr(97+y)
def neighbors(p):
    x,y=p
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny=x+dx,y+dy
        if 0<=nx<19 and 0<=ny<19: yield (nx,ny)
def group_libs(board,start):
    col=board[start]; vis=set([start]); stack=[start]; libs=set()
    while stack:
        cur=stack.pop()
        for nb in neighbors(cur):
            if nb not in board: libs.add(nb)
            elif board[nb]==col and nb not in vis:
                vis.add(nb); stack.append(nb)
    return vis,libs
def has_zero(board):
    seen=set()
    for p in board:
        if p in seen: continue
        g,l=group_libs(board,p); seen|=g
        if len(l)==0: return p
    return None
def apply(board,color,coord):
    p=to_pos(coord)
    if p in board: return None,"occupied"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suicide"
    return nb,None
def mkboard(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b

# We'll attempt to create 10 validated problems by manual design with increasing depth
# Template helper to build SGF string

def sgf_string(ab,aw, variations):
    # variations: list of (seq_list, is_right) where seq_list = [(color,coord),...]
    # First move color determines solver. We'll assume first variation's first color is solver.
    ab_s="".join(f"[{s}]" for s in sorted(set(ab)))
    aw_s="".join(f"[{s}]" for s in sorted(set(aw)))
    parts=[]
    for seq, is_right in variations:
        # build chain: (;B[xx];W[yy]...C[RIGHT] if right)
        chain=""
        for i,(col,coord) in enumerate(seq):
            is_last=i==len(seq)-1
            if is_right and is_last:
                chain+=f";{col}[{coord}]C[RIGHT]"
            else:
                chain+=f";{col}[{coord}]"
        parts.append(f"({chain})")
    return f"(;SZ[19]AB{ab_s}AW{aw_s}" + "".join(parts) + ")"

# Problem 1: Easy Black to kill, 1-move capture at center area (r9 region)
# Design: White 2 stones at nn/on, Black surrounds leaving op as vital
# Use board center-right
ab1=["mm","nm","om","pm","qm","mn","pn","qn","mo","po","qo","mp","qp","mq","nq","oq","pq","nr","or","pr","ns","os","ps"]
# That's too many. Simpler.
# Let's design minimal wall: 3 white stones L shape, 8 black stones around
ab1 = ["mn","nn","on","pn","qn","mo","qo","mp","qp","mq","nq","oq","pq"]
# This encloses area but leaves gap ?
# Let's test specific leave: vital = op (14,15?) Wait coordinate system: a=0. mn = (12,13)? Need compute.
# mn = m(12), n(13) -> (12,13). op = o(14) p(15) -> (14,15)
# Let's brute search around centre o=14? We'll just brute force a design with 1 capture

# Better to brute generate each problem programmatically with search, then verify

def find_kill_brute(center_sgf, white_shape, outer_radius=2):
    # white_shape: list of sgf relative to center? We'll place at center
    cx,cy=to_pos(center_sgf)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_shape]
    # candidate liberties: neighbors of white group
    btmp=mkboard([], aw_abs)
    neigh=set()
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in btmp: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    # Try to surround: iterate subsets of neigh to keep as empty, rest occupied by black
    # For easy: 2 empty leaves (one kill, one fail)
    for leave in itertools.combinations(neigh, 2):
        leave_set=set(leave)
        black_nei=[s for s in neigh if s not in leave_set]
        # add outer shell to make black wall solid (distance 2)
        outer=[]
        for x in range(cx-3,cx+4):
            for y in range(cy-3,cy+4):
                if 0<=x<19 and 0<=y<19:
                    s=to_sgf(x,y)
                    if s in aw_abs or s in leave_set or s in black_nei:
                        continue
                    # Manhattan distance 2-3
                    md=max(abs(x-cx), abs(y-cy))
                    if md==3:
                        outer.append(s)
        ab=black_nei+outer[:12]  # limit stones
        ab=[s for s in ab if s not in aw_abs]
        b=mkboard(ab, aw_abs)
        if has_zero(b): continue
        # check white group liberties count matches leave size (or maybe more due to outer not blocking diagonals)
        # Find white group libs
        g,l=group_libs(b, to_pos(aw_abs[0]))
        if len(l)!=len(leave): continue
        # test killing move captures
        kill=None; fail=None
        for mv in leave:
            nb,err=apply(b,'B',mv)
            if err: continue
            if to_pos(aw_abs[0]) not in nb:
                kill=mv
            else:
                fail=mv
        if kill and fail:
            # ensure fail move not also kill (we did) and fail leaves white with at least 1 lib
            # verify after fail, white still has libs >0 (obviously)
            nb2,_=apply(b,'B',fail)
            if nb2 and to_pos(aw_abs[0]) in nb2:
                return ab, aw_abs, kill, fail, b
    return None

# Test P1
res1=find_kill_brute("nn", [(0,0),(1,0),(0,1)])  # L shape at nn
print("res1", res1)
if res1:
    ab,aw,kill,fail,b=res1
    print(f"P1 kill {kill} fail {fail} AB {len(ab)} AW {len(aw)}")
    sgf=sgf_string(ab,aw, [([("B",kill)], True), ([("B",fail),("W",kill)], False)])
    pathlib.Path("outputs/problem-01.sgf").write_text(sgf)
    print(sgf)

# P2: White to kill, mirror colors
res2=find_kill_brute("jj", [(0,0),(1,0),(0,1)])
if res2:
    ab,aw,kill,fail,b=res2
    # swap colors: black becomes victim, white kills
    # Swap AB/AW roles
    sgf=sgf_string(aw, ab, [([("W",kill)], True), ([("W",fail),("B",kill)], False)])
    pathlib.Path("outputs/problem-02.sgf").write_text(sgf)
    print("P2", sgf)

