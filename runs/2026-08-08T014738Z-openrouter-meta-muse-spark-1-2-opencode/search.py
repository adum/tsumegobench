import pathlib, re, itertools, random
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
    return nb,None
def mkboard(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b
def sgf_str(ab,aw,variations):
    ab_s="".join(f"[{s}]" for s in sorted(set(ab)))
    aw_s="".join(f"[{s}]" for s in sorted(set(aw)))
    parts=[]
    for seq,right in variations:
        chain=""
        for i,(c,coord) in enumerate(seq):
            is_last=i==len(seq)-1
            if right and is_last: chain+=f";{c}[{coord}]C[RIGHT]"
            else: chain+=f";{c}[{coord}]"
        parts.append(f"({chain})")
    return f"(;SZ[19]AB{ab_s}AW{aw_s}"+"".join(parts)+")"
def is_dead(board, core): return to_pos(core) not in board

def find_one(center, white_rel, seed):
    random.seed(seed)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_rel]
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[to_sgf(x,y) for x in range(cx-4,cx+5) for y in range(cy-4,cy+5) if 0<=x<19 and 0<=y<19 and to_sgf(x,y) not in aw_abs and to_sgf(x,y) not in neigh]
    for _ in range(5000):
        leave=random.sample(neigh,2)
        leave_set=set(leave)
        black_neigh=[s for s in neigh if s not in leave_set]
        outer_choice=random.sample(outer_pool, min(10, len(outer_pool)))
        ab=black_neigh+outer_choice
        ab=[s for s in dict.fromkeys(ab) if s not in aw_abs]
        b=mkboard(ab, aw_abs)
        if has_zero(b): continue
        try: g,l=group_libs(b, to_pos(aw_abs[0]))
        except: continue
        if set(to_sgf(*p) for p in l)!=leave_set: continue
        kill=None; fail=None
        for mv in leave:
            nb,err=apply(b,'B',mv)
            if err: continue
            if is_dead(nb, aw_abs[0]): kill=mv
            else: fail=mv
        if kill and fail: return ab, aw_abs, kill, fail, b
    return None

def find_snap(center, white_rel, seed):
    random.seed(seed+100)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_rel]
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[to_sgf(x,y) for x in range(cx-4,cx+5) for y in range(cy-4,cy+5) if 0<=x<19 and 0<=y<19 and to_sgf(x,y) not in aw_abs and to_sgf(x,y) not in neigh]
    for _ in range(6000):
        leave=random.sample(neigh,2)
        leave_set=set(leave)
        black_neigh=[s for s in neigh if s not in leave_set]
        outer_choice=random.sample(outer_pool, min(12, len(outer_pool)))
        ab=black_neigh+outer_choice
        ab=[s for s in dict.fromkeys(ab) if s not in aw_abs]
        b=mkboard(ab, aw_abs)
        if has_zero(b): continue
        try: g,l=group_libs(b, to_pos(aw_abs[0]))
        except: continue
        if set(to_sgf(*p) for p in l)!=leave_set: continue
        for throw in leave:
            other=leave[1] if leave[0]==throw else leave[0]
            b1,err=apply(b,'B',throw)
            if err: continue
            found_w=None
            for wmv in neigh+outer_choice:
                if wmv==throw: continue
                if to_pos(wmv) in b1: continue
                b2,err2=apply(b1,'W',wmv)
                if err2: continue
                if to_pos(throw) not in b2 and to_pos(throw) in b1:
                    found_w=wmv; break
            if not found_w: continue
            b2,_=apply(b1,'W',found_w)
            for brec in [throw, other]:
                if to_pos(brec) in b2: continue
                b3,err3=apply(b2,'B',brec)
                if err3: continue
                if is_dead(b3, aw_abs[0]):
                    b_alt,err_alt=apply(b,'B',other)
                    if err_alt: continue
                    if is_dead(b_alt, aw_abs[0]): continue
                    return ab, aw_abs, throw, other, found_w, brec, b
    return None

# Try to find for 10 centers
configs=[
    ("nn", [(0,0),(1,0),(0,1)], 1),
    ("jj", [(0,0),(1,0)], 2),
    ("dd", [(0,0),(1,0),(0,1)], 33),
    ("qq", [(0,0),(0,1)], 44),
    ("kk", [(0,0),(1,0)], 5),
    ("mm", [(0,0),(0,1)], 6),
    ("gg", [(0,0),(1,0),(0,1)], 7),
    ("cc", [(0,0),(1,0)], 8),
    ("rr", [(0,0),(1,0),(0,1),(1,1)], 9),
    ("pp", [(0,0),(0,1),(1,0)], 10),
]

for idx,(center,rel,seed) in enumerate(configs):
    is_snap = idx>=4
    if is_snap:
        res=find_snap(center, rel, seed*10+idx)
        print(f"{idx+1} snap {res is not None}")
        if res:
            ab,aw,throw,other,wcap,brec,b=res
            print(f"  throw {throw} other {other} wcap {wcap} brec {brec} AB {len(ab)}")
        else:
            res=find_one(center, rel, seed*10+idx)
            print(f"  fallback one {res is not None}")
            if res:
                ab,aw,kill,fail,b=res
                print(f"    kill {kill} fail {fail}")
    else:
        res=find_one(center, rel, seed*10+idx)
        print(f"{idx+1} one {res is not None}")
        if res:
            ab,aw,kill,fail,b=res
            print(f"  kill {kill} fail {fail} AB {len(ab)}")
