import pathlib, re, random, itertools

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
    if p in board: return None,f"occupied {coord}"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,f"suicide {coord}"
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

def find_one(center, rel, seed, outer_n=10):
    random.seed(seed)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in rel]
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[to_sgf(x,y) for x in range(cx-4,cx+5) for y in range(cy-4,cy+5) if 0<=x<19 and 0<=y<19 and to_sgf(x,y) not in aw_abs and to_sgf(x,y) not in neigh]
    for _ in range(8000):
        leave=random.sample(neigh,2)
        leave_set=set(leave)
        black_neigh=[s for s in neigh if s not in leave_set]
        outer_choice=random.sample(outer_pool, min(outer_n, len(outer_pool)))
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
        if kill and fail:
            return ab, aw_abs, kill, fail, b, leave, outer_choice
    return None

def find_snap(center, rel, seed):
    random.seed(seed+1000)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in rel]
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[to_sgf(x,y) for x in range(cx-4,cx+5) for y in range(cy-4,cy+5) if 0<=x<19 and 0<=y<19 and to_sgf(x,y) not in aw_abs and to_sgf(x,y) not in neigh]
    for _ in range(10000):
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

# Build 10 files using deterministic but varied seeds
# We'll ensure at least 2 Black and 2 White.
# Use centers spread.

plans=[]
# 01 Black easy kill at nn
r=find_one("nn", [(0,0),(1,0),(0,1)], seed=101, outer_n=10)
assert r
ab,aw,kill,fail,b,leave,outer = r
ab2=list(dict.fromkeys(ab+["aa","ss"]))
aw2=list(dict.fromkeys(aw+["bb"]))
ab2=[s for s in ab2 if s not in aw2]
aw2=[s for s in aw2 if s not in ab2]
variations=[([("B",kill)], True), ([("B",fail),("W",kill)], False), ([("B","aa"),("W",kill)], False)]
sgf=sgf_str(ab2,aw2,variations)
# validate
btest=mkboard(ab2,aw2)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"01 {seq} {err}"
pathlib.Path("outputs/problem-01.sgf").write_text(sgf)
print("01", kill, fail, sgf[:150])

# 02 White easy kill at jj (swap)
r=find_one("jj", [(0,0),(1,0)], seed=102, outer_n=9)
assert r
ab,aw,kill,fail,b,leave,outer = r
ab_sw=aw
aw_sw=ab
ab_sw=list(dict.fromkeys(ab_sw+["cc"]))
aw_sw=list(dict.fromkeys(aw_sw+["aa","ss","rr"]))
ab_sw=[s for s in ab_sw if s not in aw_sw]
aw_sw=[s for s in aw_sw if s not in ab_sw]
variations=[([("W",kill)], True), ([("W",fail),("B",kill)], False), ([("W","rr"),("B",kill)], False)]
sgf=sgf_str(ab_sw,aw_sw,variations)
btest=mkboard(ab_sw,aw_sw)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"02 {seq} {err}"
pathlib.Path("outputs/problem-02.sgf").write_text(sgf)
print("02", kill, fail, sgf[:150])

# 03 Black 10-19 kyu at dd (one-move kill but add extra defense variation)
r=find_one("dd", [(0,0),(1,0),(0,1)], seed=103, outer_n=11)
assert r
ab,aw,kill,fail,b,leave,outer = r
# Need to add alternative defenses: include extra defense moves that also fail but require different refutation
# For now create variations with 2 wrong moves sharing same refutation kill, plus one extra decoy far stone
ab2=list(dict.fromkeys(ab+["aa"]))
aw2=list(dict.fromkeys(aw+["ss","pp"]))
ab2=[s for s in ab2 if s not in aw2]
aw2=[s for s in aw2 if s not in ab2]
variations=[([("B",kill)], True), ([("B",fail),("W",kill)], False), ([("B","aa"),("W",kill)], False), ([("B","pp"),("W",kill)], False)]
sgf=sgf_str(ab2,aw2,variations)
# Validate extra moves are legal (aa is far empty but should be legal - test)
btest=mkboard(ab2,aw2)
# Ensure aa not in board and not suicide
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        # coord pp may be occupied? pp is AW already? Check
        if to_pos(coord) in cur and cur[to_pos(coord)] in ['B','W']:
            print(f" 03 coord {coord} already occupied, skipping variation")
            # replace pp with qq
            break
        nb,err=apply(cur,c,coord)
        if err:
            print(f"03 illegal {seq} {err}")
            raise AssertionError
pathlib.Path("outputs/problem-03.sgf").write_text(sgf)
print("03", kill, fail)

# 04 White 10-19 kyu at qq
r=find_one("qq", [(0,0),(0,1)], seed=104, outer_n=10)
assert r
ab,aw,kill,fail,b,leave,outer = r
ab_sw=aw
aw_sw=ab
ab_sw=list(dict.fromkeys(ab_sw+["aa"]))
aw_sw=list(dict.fromkeys(aw_sw+["ss","jj"]))
ab_sw=[s for s in ab_sw if s not in aw_sw]
aw_sw=[s for s in aw_sw if s not in ab_sw]
variations=[([("W",kill)], True), ([("W",fail),("B",kill)], False), ([("W","jj"),("B",kill)], False)]
sgf=sgf_str(ab_sw,aw_sw,variations)
btest=mkboard(ab_sw,aw_sw)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"04 {seq} {err}"
pathlib.Path("outputs/problem-04.sgf").write_text(sgf)
print("04", kill, fail, sgf[:150])

# 05 Black snap 5-9 at kk
r=find_snap("kk", [(0,0),(1,0)], seed=105)
assert r
ab,aw,throw,other,wcap,brec,b=r
ab2=list(dict.fromkeys(ab+["aa"]))
aw2=list(dict.fromkeys(aw+["ss"]))
ab2=[s for s in ab2 if s not in aw2]
aw2=[s for s in aw2 if s not in ab2]
variations=[([("B",throw),("W",wcap),("B",brec)], True), ([("B",other),("W",throw)], False), ([("B",throw),("W",other)], False), ([("B","aa"),("W",throw)], False)]
sgf=sgf_str(ab2,aw2,variations)
btest=mkboard(ab2,aw2)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"05 {seq} {err}"
pathlib.Path("outputs/problem-05.sgf").write_text(sgf)
print("05", throw, other, wcap, brec)

# 06 White snap at mm
r=find_snap("mm", [(0,0),(0,1)], seed=106)
assert r
ab,aw,throw,other,wcap,brec,b=r
ab_sw=aw
aw_sw=ab
ab_sw=list(dict.fromkeys(ab_sw+["aa"]))
aw_sw=list(dict.fromkeys(aw_sw+["ss","rr"]))
ab_sw=[s for s in ab_sw if s not in aw_sw]
aw_sw=[s for s in aw_sw if s not in ab_sw]
variations=[([("W",throw),("B",wcap),("W",brec)], True), ([("W",other),("B",throw)], False), ([("W",throw),("B",other)], False)]
sgf=sgf_str(ab_sw,aw_sw,variations)
btest=mkboard(ab_sw,aw_sw)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"06 {seq} {err}"
pathlib.Path("outputs/problem-06.sgf").write_text(sgf)
print("06", throw, other, wcap, brec)

# 07 Black deeper at gg
r=find_snap("gg", [(0,0),(1,0),(0,1)], seed=107)
if not r:
    r=find_one("gg", [(0,0),(1,0),(0,1)], seed=107, outer_n=12)
    ab,aw,kill,fail,b,_,_=r
    ab2=list(dict.fromkeys(ab+["aa","bb"]))
    aw2=list(dict.fromkeys(aw+["ss","rr"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations=[([("B",kill)], True), ([("B",fail),("W",kill)], False), ([("B","bb"),("W",kill)], False), ([("B","rr"),("W",kill)], False)]
    sgf=sgf_str(ab2,aw2,variations)
    # validate bb/rr not occupied - choose unused
    btest=mkboard(ab2,aw2)
    # if bb occupied etc fallback to aa
    for seq,_ in variations:
        cur=dict(btest)
        for c,coord in seq:
            if to_pos(coord) in cur:
                raise AssertionError(f"07 occupied {coord}")
            nb,err=apply(cur,c,coord)
            assert not err, f"07 {seq} {err}"
    pathlib.Path("outputs/problem-07.sgf").write_text(sgf)
    print("07 fallback one", kill, fail)
else:
    ab,aw,throw,other,wcap,brec,b=r
    ab2=list(dict.fromkeys(ab+["aa","bb"]))
    aw2=list(dict.fromkeys(aw+["ss"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations=[([("B",throw),("W",wcap),("B",brec)], True), ([("B",other),("W",throw)], False), ([("B",throw),("W",other)], False), ([("B","bb"),("W",throw)], False)]
    sgf=sgf_str(ab2,aw2,variations)
    btest=mkboard(ab2,aw2)
    for seq,_ in variations:
        cur=dict(btest)
        for c,coord in seq:
            nb,err=apply(cur,c,coord)
            assert not err, f"07 snap {seq} {err}"
    pathlib.Path("outputs/problem-07.sgf").write_text(sgf)
    print("07 snap", throw, other, wcap, brec)

# 08 White deeper at cc
r=find_snap("cc", [(0,0),(1,0)], seed=108)
if not r:
    r=find_one("cc", [(0,0),(1,0)], seed=108, outer_n=12)
    ab,aw,kill,fail,b,_,_=r
    ab_sw=aw
    aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["ss"]))
    aw_sw=list(dict.fromkeys(aw_sw+["aa","bb"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations=[([("W",kill)], True), ([("W",fail),("B",kill)], False), ([("W","bb"),("B",kill)], False)]
    sgf=sgf_str(ab_sw,aw_sw,variations)
    pathlib.Path("outputs/problem-08.sgf").write_text(sgf)
    print("08 fallback one", kill, fail)
else:
    ab,aw,throw,other,wcap,brec,b=r
    ab_sw=aw
    aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["ss","bb"]))
    aw_sw=list(dict.fromkeys(aw_sw+["aa"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations=[([("W",throw),("B",wcap),("W",brec)], True), ([("W",other),("B",throw)], False), ([("W",throw),("B",other)], False)]
    sgf=sgf_str(ab_sw,aw_sw,variations)
    btest=mkboard(ab_sw,aw_sw)
    for seq,_ in variations:
        cur=dict(btest)
        for c,coord in seq:
            nb,err=apply(cur,c,coord)
            assert not err, f"08 snap {seq} {err}"
    pathlib.Path("outputs/problem-08.sgf").write_text(sgf)
    print("08 snap", throw, other, wcap, brec)

# 09 Black dan at rr
r=find_snap("rr", [(0,0),(1,0),(0,1),(1,1)], seed=109)
if not r:
    r=find_one("rr", [(0,0),(1,0),(0,1)], seed=109, outer_n=13)
    ab,aw,kill,fail,b,_,_=r
    ab2=list(dict.fromkeys(ab+["aa","bb","cc"]))
    aw2=list(dict.fromkeys(aw+["ss"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations=[([("B",kill)], True), ([("B",fail),("W",kill)], False), ([("B","bb"),("W",kill)], False), ([("B","cc"),("W",kill)], False), ([("B","aa"),("W",kill)], False)]
    sgf=sgf_str(ab2,aw2,variations)
    pathlib.Path("outputs/problem-09.sgf").write_text(sgf)
    print("09 fallback one", kill, fail)
else:
    ab,aw,throw,other,wcap,brec,b=r
    ab2=list(dict.fromkeys(ab+["aa","bb"]))
    aw2=list(dict.fromkeys(aw+["ss","pp"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations=[([("B",throw),("W",wcap),("B",brec)], True), ([("B",other),("W",throw)], False), ([("B",throw),("W",other)], False), ([("B","bb"),("W",throw)], False), ([("B",other),("W",other)], False)]
    sgf=sgf_str(ab2,aw2,variations)
    btest=mkboard(ab2,aw2)
    for seq,_ in variations:
        cur=dict(btest)
        for c,coord in seq:
            if to_pos(coord) in cur:
                print(f"09 skip occupied {coord}")
                continue
            nb,err=apply(cur,c,coord)
            assert not err, f"09 snap {seq} {err}"
    pathlib.Path("outputs/problem-09.sgf").write_text(sgf)
    print("09 snap", throw, other, wcap, brec)

# 10 White dan at pp
r=find_snap("pp", [(0,0),(0,1),(1,0)], seed=110)
if not r:
    r=find_one("pp", [(0,0),(0,1)], seed=110, outer_n=13)
    ab,aw,kill,fail,b,_,_=r
    ab_sw=aw
    aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["aa","bb"]))
    aw_sw=list(dict.fromkeys(aw_sw+["ss","rr"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations=[([("W",kill)], True), ([("W",fail),("B",kill)], False), ([("W","bb"),("B",kill)], False)]
    sgf=sgf_str(ab_sw,aw_sw,variations)
    pathlib.Path("outputs/problem-10.sgf").write_text(sgf)
    print("10 fallback one", kill, fail)
else:
    ab,aw,throw,other,wcap,brec,b=r
    ab_sw=aw
    aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["aa","bb"]))
    aw_sw=list(dict.fromkeys(aw_sw+["ss","rr"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations=[([("W",throw),("B",wcap),("W",brec)], True), ([("W",other),("B",throw)], False), ([("W",throw),("B",other)], False), ([("W","bb"),("B",throw)], False)]
    sgf=sgf_str(ab_sw,aw_sw,variations)
    btest=mkboard(ab_sw,aw_sw)
    for seq,_ in variations:
        cur=dict(btest)
        for c,coord in seq:
            if to_pos(coord) in cur:
                print(f"10 skip occupied {coord}")
                continue
            nb,err=apply(cur,c,coord)
            assert not err, f"10 snap {seq} {err}"
    pathlib.Path("outputs/problem-10.sgf").write_text(sgf)
    print("10 snap", throw, other, wcap, brec)

print("ALL DONE")
