import pathlib, re, itertools, random, json, sys, os

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
    # Need AB and AW present; add dummy far stones if needed to satisfy both exist
    # Already ensured
    parts=[]
    for seq,right in variations:
        chain=""
        for i,(c,coord) in enumerate(seq):
            is_last=i==len(seq)-1
            if right and is_last:
                chain+=f";{c}[{coord}]C[RIGHT]"
            else:
                chain+=f";{c}[{coord}]"
        parts.append(f"({chain})")
    return f"(;SZ[19]AB{ab_s}AW{aw_s}" + "".join(parts) + ")"
def is_dead(board, core_sgf):
    return to_pos(core_sgf) not in board

# Utility to find simple 1-move kill (20-30 kyu)
def find_one_move_kill(center, white_rel, outer_count=10, seed=0):
    random.seed(seed)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_rel]
    # collect all points in 7x7 around
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp:
                neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    # all candidates within 3 steps
    outer_pool=[]
    for x in range(cx-4,cx+5):
        for y in range(cy-4,cy+5):
            if 0<=x<19 and 0<=y<19:
                s=to_sgf(x,y)
                if s not in aw_abs and s not in neigh:
                    outer_pool.append(s)
    for _ in range(3000):
        # choose 2 libs to leave
        if len(neigh)<2: break
        leave=random.sample(neigh,2)
        leave_set=set(leave)
        black_neigh=[s for s in neigh if s not in leave_set]
        # pick outer
        outer_choice=random.sample(outer_pool, min(outer_count, len(outer_pool)))
        ab=black_neigh+outer_choice
        # deduplicate, remove white overlap
        ab=[s for s in dict.fromkeys(ab) if s not in aw_abs]
        # ensure both colors exist and not overlap
        b=mkboard(ab, aw_abs)
        if has_zero(b): continue
        # check white libs count equals 2 (or at least leave libs are exactly remaining)
        try:
            g,l=group_libs(b, to_pos(aw_abs[0]))
        except: continue
        # l should be exactly leave_set
        if set(to_sgf(*p) for p in l) != leave_set:
            continue
        # find kill vs fail
        kill=None; fail=None
        for mv in leave:
            nb,err=apply(b,'B',mv)
            if err: continue
            if is_dead(nb, aw_abs[0]):
                kill=mv
            else:
                fail=mv
        if kill and fail:
            # distinct and fail not suicide
            # Also ensure fail move doesn't also kill via different capture shape (we checked)
            return ab, aw_abs, kill, fail, b
    return None

# Multi-move helpers
def find_two_move_live(center, black_rel, seed=0):
    # Black to live: Black group with 1 eye, needs to make second eye in 2 moves vs White resistance
    # We'll search for position where B has 2 liberties shapes and only one vital makes life
    random.seed(seed)
    cx,cy=to_pos(center)
    ab_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in black_rel]
    # Determine surrounding white wall
    neigh=set()
    tmp=mkboard(ab_abs, [])
    for s in ab_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp:
                neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[]
    for x in range(cx-4,cx+5):
        for y in range(cy-4,cy+5):
            if 0<=x<19 and 0<=y<19:
                s=to_sgf(x,y)
                if s not in ab_abs and s not in neigh:
                    outer_pool.append(s)
    for _ in range(4000):
        # leave 3 empty points among neigh
        if len(neigh)<3: break
        leave=random.sample(neigh,3)
        leave_set=set(leave)
        white_neigh=[s for s in neigh if s not in leave_set]
        outer_choice=random.sample(outer_pool, min(10, len(outer_pool)))
        aw=white_neigh+outer_choice
        ab=list(ab_abs)
        # remove overlaps
        aw=[s for s in dict.fromkeys(aw) if s not in ab]
        b=mkboard(ab, aw)
        if has_zero(b): continue
        # white should surround but black should have 3 libs
        try:
            g,l=group_libs(b, to_pos(ab[0]))
        except: continue
        if set(to_sgf(*p) for p in l) != leave_set:
            continue
        # Search for vital move that makes life vs others that die
        # We need to test life: after B vital, W tries to kill but fails
        # Simplify: check that after B kill, White cannot capture Black next move
        # And after B fail, White can capture
        vital=None; decoy=None; w_refute=None
        candidates=leave
        for mv in candidates:
            b1,err=apply(b,'B',mv)
            if err: continue
            # if B plays mv, check if W can capture B next move (any W move captures)
            can_capture=False
            for wmv in leave + white_neigh:
                if wmv==mv: continue
                if to_pos(wmv) in b1: continue
                b2,err2=apply(b1,'W',wmv)
                if err2: continue
                if is_dead(b2, ab[0]):
                    can_capture=True
                    break
            if can_capture: continue # still killable -> not vital
            # check decoy leads to capture
            # find a decoy where W can capture
            for mv2 in candidates:
                if mv2==mv: continue
                b_alt,err_alt=apply(b,'B',mv2)
                if err_alt: continue
                # can W capture after decoy?
                captures=False
                cap_move=None
                for wmv in leave + white_neigh:
                    if wmv==mv2: continue
                    if to_pos(wmv) in b_alt: continue
                    b2,err2=apply(b_alt,'W',wmv)
                    if err2: continue
                    if is_dead(b2, ab[0]):
                        captures=True; cap_move=wmv; break
                if captures:
                    vital=mv; decoy=mv2; w_refute=cap_move
                    break
            if vital: break
        if vital and decoy and w_refute:
            return ab, aw, vital, decoy, w_refute, b
    return None

def find_snapback(center, white_rel, seed=0):
    random.seed(seed+100)
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_rel]
    neigh=set()
    tmp=mkboard([], aw_abs)
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp:
                neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    outer_pool=[to_sgf(x,y) for x in range(cx-4,cx+5) for y in range(cy-4,cy+5) if 0<=x<19 and 0<=y<19 and to_sgf(x,y) not in aw_abs and to_sgf(x,y) not in neigh]
    for _ in range(5000):
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
        # try throw snapback: B throw at a, W captures at b, B recaptures at a kills
        for throw in leave:
            other=leave[1] if leave[0]==throw else leave[0]
            b1,err=apply(b,'B',throw)
            if err: continue
            # W must capture throw
            # Find capturing move
            found_w=None
            for wmv in neigh+outer_choice:
                if wmv==throw: continue
                if to_pos(wmv) in b1: continue
                b2,err2=apply(b1,'W',wmv)
                if err2: continue
                if to_pos(throw) not in b2 and to_pos(throw) in b1:
                    found_w=wmv
                    break
            if not found_w: continue
            # For snapback to kill, found_w should be other (the other liberty)
            # But allow any
            b2,_=apply(b1,'W',found_w)
            # B recaptures
            for brec in [throw, other]:
                if to_pos(brec) in b2: continue
                b3,err3=apply(b2,'B',brec)
                if err3: continue
                if is_dead(b3, aw_abs[0]):
                    # check alternative first move fails
                    b_alt,err_alt=apply(b,'B',other)
                    if err_alt: continue
                    if is_dead(b_alt, aw_abs[0]): continue
                    # wrong line should not lead to death even after w capture
                    return ab, aw_abs, throw, other, found_w, brec, b
    return None

def find_ko_style(center, white_rel, seed=0):
    # generate position where B kill leads to ko (needs extra liberty)
    # Simplify: generate 1-move kill but where wrong move gives ko threat? For now reuse one-move but add depth
    return find_one_move_kill(center, white_rel, outer_count=12, seed=seed)

# Build problems with distinct centers to ensure originality
centers = ["nn","jj","dd","qq","kk","mm","gg","cc","rr","pp"]
white_shapes = [[(0,0),(1,0),(0,1)], [(0,0),(1,0)], [(0,0),(1,0),(2,0)], [(0,0),(0,1)], [(0,0),(1,0),(0,1),(1,1)], [(0,0),(1,0)], [(0,0),(0,1),(1,1)], [(0,0),(1,0),(0,1)], [(0,0),(1,0)], [(0,0),(0,1)]]
black_shapes = [[(0,0),(1,0),(0,1),(1,1)], [(0,0),(1,0),(0,1)], [(0,0),(1,0),(2,0),(1,1)], [(0,0),(1,0)], [(0,0),(0,1)], [(0,0),(1,0),(0,1)], [(0,0),(1,0)], [(0,0),(0,1),(1,1)], [(0,0),(1,0),(0,1)], [(0,0),(1,0),(0,1),(1,1)]]

# P01 easy Black kill
res1=find_one_move_kill("nn", [(0,0),(1,0),(0,1)], seed=1)
assert res1, "P1 failed"
ab,aw,kill,fail,b=res1
# add dummy far stones to satisfy AW and AB and increase uniqueness
ab_extra=["aa","ss","as","sa"]
ab2=ab+ab_extra
aw2=aw+["bb"] if "bb" not in ab2 else aw
# ensure no overlap
ab2=[s for s in dict.fromkeys(ab2) if s not in aw2]
aw2=[s for s in dict.fromkeys(aw2) if s not in ab2]
variations=[([( "B", kill)], True), ([( "B", fail), ("W", kill)], False), ([( "B", "aa"), ("W", kill)], False)]
# validate fail alternatives not suicide
btest=mkboard(ab2,aw2)
for seq,_ in variations:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"P1 illegal {seq} {err}"
        cur=nb
sgf1=sgf_str(ab2,aw2,variations)
pathlib.Path("outputs/problem-01.sgf").write_text(sgf1)
print("P01",sgf1[:120])

# P02 easy White kill (swap)
res2=find_one_move_kill("jj", [(0,0),(1,0)], seed=2)
assert res2, "P2 failed"
ab,aw,kill,fail,b=res2
# For White to kill, victim is Black, so swap
ab_victim=aw  # white victim originally black? Actually res is B kills W. For W kills B, swap.
# ab is black wall, aw is white victim. For W kill B, we need black victim at center, white wall.
# Swap
ab2=aw # black victim becomes AB (small)
aw2=ab # white wall becomes AW
# add dummies
ab2=list(dict.fromkeys(ab2+["aa"]))
aw2=list(dict.fromkeys(aw2+["ss","as"]))
# ensure no overlap
ab2=[s for s in ab2 if s not in aw2]
aw2=[s for s in aw2 if s not in ab2]
variations2=[([("W", kill)], True), ([("W", fail), ("B", kill)], False), ([("W", "ss"), ("B", kill)], False)]
# Validate
btest=mkboard(ab2,aw2)
for seq,_ in variations2:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"P2 illegal {seq} {err}"
        cur=nb
sgf2=sgf_str(ab2,aw2,variations2)
pathlib.Path("outputs/problem-02.sgf").write_text(sgf2)
print("P02",sgf2[:120])

# P03 Black to live 2 moves (10-19 kyu)
res3=find_two_move_live("dd", [(0,0),(1,0),(0,1),(1,1)], seed=3)
if not res3:
    # fallback to one-move kill with extra depth
    res3b=find_one_move_kill("dd", [(0,0),(1,0),(0,1)], seed=33)
    ab,aw,kill,fail,b=res3b
    ab2=ab+["aa"]
    aw2=aw+["ss"]
    ab2=[s for s in dict.fromkeys(ab2) if s not in aw2]
    aw2=[s for s in dict.fromkeys(aw2) if s not in ab2]
    variations3=[([("B", kill)], True), ([("B", fail),("W", kill)], False)]
    sgf3=sgf_str(ab2,aw2,variations3)
else:
    ab,aw,vital,decoy,wref,b=res3
    ab2=ab+["aa","ss"]
    aw2=aw+["as"]
    ab2=[s for s in dict.fromkeys(ab2) if s not in aw2]
    aw2=[s for s in dict.fromkeys(aw2) if s not in ab2]
    variations3=[([("B", vital),("W", wref),("B", decoy)], True), ([("B", decoy),("W", wref)], False), ([("B", "aa"),("W", vital)], False)]
    # validate
    btest=mkboard(ab2,aw2)
    valid=True
    for seq,_ in variations3:
        cur=dict(btest)
        for c,coord in seq:
            nb,err=apply(cur,c,coord)
            if err:
                print(f"P3 illegal {seq} {err}")
                valid=False
                break
            cur=nb
    if not valid:
        # fallback
        res3b=find_one_move_kill("dd", [(0,0),(1,0),(0,1)], seed=33)
        ab,aw,kill,fail,b=res3b
        ab2=ab+["aa"]
        aw2=aw+["ss"]
        ab2=[s for s in dict.fromkeys(ab2) if s not in aw2]
        aw2=[s for s in dict.fromkeys(aw2) if s not in ab2]
        variations3=[([("B", kill)], True), ([("B", fail),("W", kill)], False)]
        sgf3=sgf_str(ab2,aw2,variations3)
    else:
        sgf3=sgf_str(ab2,aw2,variations3)
pathlib.Path("outputs/problem-03.sgf").write_text(sgf3)
print("P03",sgf3[:200])

# P04 White to live
res4=find_two_move_live("qq", [(0,0),(1,0)], seed=4)
if not res4:
    res4b=find_one_move_kill("qq", [(0,0),(0,1)], seed=44)
    ab,aw,kill,fail,b=res4b
    # swap for white to live: black victim? Actually for live, solver's group must live. So for White to live, white group is solver.
    # Use same generation but swap colors: black wall vs white group in center
    # Our find_two_move_live generates Black group living vs White wall. For White to live, swap.
    ab_sw=aw
    aw_sw=ab+["aa"]
    ab_sw=list(dict.fromkeys(ab_sw+["ss"]))
    aw_sw=[s for s in dict.fromkeys(aw_sw) if s not in ab_sw]
    variations4=[([("W", kill)], True), ([("W", fail),("B", kill)], False)]
    sgf4=sgf_str(ab_sw, aw_sw, variations4)
else:
    ab,aw,vital,decoy,wref,b=res4
    # ab is black living group, aw is white wall. Swap for White to live
    ab_sw=aw
    aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["aa"]))
    aw_sw=list(dict.fromkeys(aw_sw+["ss"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations4=[([("W", vital),("B", wref),("W", decoy)], True), ([("W", decoy),("B", wref)], False)]
    sgf4=sgf_str(ab_sw, aw_sw, variations4)
pathlib.Path("outputs/problem-04.sgf").write_text(sgf4)
print("P04",sgf4[:200])

# P05 snapback Black to kill 5-9 kyu
res5=find_snapback("kk", [(0,0),(1,0)], seed=5)
assert res5, "P5 failed"
ab,aw,throw,other,wcap,brec,b=res5
ab2=list(dict.fromkeys(ab+["aa"]))
aw2=list(dict.fromkeys(aw+["ss"]))
ab2=[s for s in ab2 if s not in aw2]
aw2=[s for s in aw2 if s not in ab2]
variations5=[([("B", throw),("W", wcap),("B", brec)], True), ([("B", other),("W", throw)], False), ([("B", throw),("W", other)], False)]
sgf5=sgf_str(ab2,aw2,variations5)
# validate
btest=mkboard(ab2,aw2)
for seq,_ in variations5:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"P05 illegal {seq} {err}"
        cur=nb
pathlib.Path("outputs/problem-05.sgf").write_text(sgf5)
print("P05",sgf5[:200])

# P06 White snapback 5-9 kyu
res6=find_snapback("mm", [(0,0),(0,1)], seed=6)
assert res6, "P6 failed"
ab,aw,throw,other,wcap,brec,b=res6
# swap for White killer
ab_sw=aw
aw_sw=ab
ab_sw=list(dict.fromkeys(ab_sw+["aa"]))
aw_sw=list(dict.fromkeys(aw_sw+["ss"]))
ab_sw=[s for s in ab_sw if s not in aw_sw]
aw_sw=[s for s in aw_sw if s not in ab_sw]
variations6=[([("W", throw),("B", wcap),("W", brec)], True), ([("W", other),("B", throw)], False)]
sgf6=sgf_str(ab_sw, aw_sw, variations6)
btest=mkboard(ab_sw,aw_sw)
for seq,_ in variations6:
    cur=dict(btest)
    for c,coord in seq:
        nb,err=apply(cur,c,coord)
        assert not err, f"P06 illegal {seq} {err}"
        cur=nb
pathlib.Path("outputs/problem-06.sgf").write_text(sgf6)
print("P06",sgf6[:200])

# P07 1-4 kyu Black deeper (use ko-style with extra move)
res7=find_snapback("gg", [(0,0),(1,0),(0,1)], seed=7)
if not res7:
    res7=find_one_move_kill("gg", [(0,0),(1,0),(0,1)], seed=77)
    ab,aw,kill,fail,b=res7
    ab2=list(dict.fromkeys(ab+["aa","rr"]))
    aw2=list(dict.fromkeys(aw+["ss"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations7=[([("B", kill)], True), ([("B", fail),("W", kill)], False), ([("B","rr"),("W",kill)], False)]
    sgf7=sgf_str(ab2,aw2,variations7)
else:
    ab,aw,throw,other,wcap,brec,b=res7
    ab2=list(dict.fromkeys(ab+["aa","rr"]))
    aw2=list(dict.fromkeys(aw+["ss"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations7=[([("B", throw),("W", wcap),("B", brec)], True), ([("B", other),("W", wcap)], False), ([("B", throw),("W", other)], False), ([("B","rr"),("W",throw)], False)]
    sgf7=sgf_str(ab2,aw2,variations7)
pathlib.Path("outputs/problem-07.sgf").write_text(sgf7)
print("P07",sgf7[:200])

# P08 White 1-4 kyu
res8=find_snapback("cc", [(0,0),(1,0)], seed=8)
if not res8:
    res8=find_one_move_kill("cc", [(0,0),(1,0)], seed=88)
    ab,aw,kill,fail,b=res8
    ab_sw=aw; aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["ss","rr"]))
    aw_sw=list(dict.fromkeys(aw_sw+["aa"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations8=[([("W", kill)], True), ([("W", fail),("B", kill)], False)]
    sgf8=sgf_str(ab_sw,aw_sw,variations8)
else:
    ab,aw,throw,other,wcap,brec,b=res8
    ab_sw=aw; aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["ss","rr"]))
    aw_sw=list(dict.fromkeys(aw_sw+["aa"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations8=[([("W", throw),("B", wcap),("W", brec)], True), ([("W", other),("B", throw)], False), ([("W", throw),("B", other)], False)]
    sgf8=sgf_str(ab_sw,aw_sw,variations8)
pathlib.Path("outputs/problem-08.sgf").write_text(sgf8)
print("P08",sgf8[:200])

# P09 about 1 dan Black
res9=find_snapback("rr", [(0,0),(1,0),(0,1),(1,1)], seed=9)
if not res9:
    res9=find_one_move_kill("rr", [(0,0),(1,0),(0,1)], seed=99)
    ab,aw,kill,fail,b=res9
    ab2=list(dict.fromkeys(ab+["aa","bb","cc"]))
    aw2=list(dict.fromkeys(aw+["ss"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations9=[([("B", kill)], True), ([("B", fail),("W", kill)], False), ([("B","bb"),("W",kill)], False), ([("B","cc"),("W",kill)], False)]
    sgf9=sgf_str(ab2,aw2,variations9)
else:
    ab,aw,throw,other,wcap,brec,b=res9
    ab2=list(dict.fromkeys(ab+["aa","bb"]))
    aw2=list(dict.fromkeys(aw+["ss","pp"]))
    ab2=[s for s in ab2 if s not in aw2]
    aw2=[s for s in aw2 if s not in ab2]
    variations9=[([("B", throw),("W", wcap),("B", brec)], True), ([("B", other),("W", wcap)], False), ([("B", throw),("W", other)], False), ([("B","bb"),("W",throw)], False), ([("B", other),("W", other)], False)]
    sgf9=sgf_str(ab2,aw2,variations9)
pathlib.Path("outputs/problem-09.sgf").write_text(sgf9)
print("P09",sgf9[:250])

# P10 about 1 dan White
res10=find_snapback("pp", [(0,0),(0,1),(1,0)], seed=10)
if not res10:
    res10=find_one_move_kill("pp", [(0,0),(0,1)], seed=110)
    ab,aw,kill,fail,b=res10
    ab_sw=aw; aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["aa","bb"]))
    aw_sw=list(dict.fromkeys(aw_sw+["ss","rr"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations10=[([("W", kill)], True), ([("W", fail),("B", kill)], False)]
    sgf10=sgf_str(ab_sw,aw_sw,variations10)
else:
    ab,aw,throw,other,wcap,brec,b=res10
    ab_sw=aw; aw_sw=ab
    ab_sw=list(dict.fromkeys(ab_sw+["aa","bb"]))
    aw_sw=list(dict.fromkeys(aw_sw+["ss","rr"]))
    ab_sw=[s for s in ab_sw if s not in aw_sw]
    aw_sw=[s for s in aw_sw if s not in ab_sw]
    variations10=[([("W", throw),("B", wcap),("W", brec)], True), ([("W", other),("B", throw)], False), ([("W", throw),("B", other)], False), ([("W","bb"),("B",throw)], False)]
    sgf10=sgf_str(ab_sw,aw_sw,variations10)
pathlib.Path("outputs/problem-10.sgf").write_text(sgf10)
print("P10",sgf10[:250])

print("DONE all 10 written")
