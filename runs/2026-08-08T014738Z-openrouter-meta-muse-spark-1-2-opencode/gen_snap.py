import itertools, random, re, pathlib, json, sys

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
def to_sgf(x,y): return chr(97+x)+chr(97+y)
def neighbors(p):
    x,y=p
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny=x+dx,y+dy
        if 0<=nx<19 and 0<=ny<19:
            yield (nx,ny)
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
    return nb, None

def mkboard(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b

def count_white(board): return sum(1 for v in board.values() if v=='W')
def count_black(board): return sum(1 for v in board.values() if v=='B')

def sgf_str(ab,aw,variations):
    ab_s="".join(f"[{s}]" for s in sorted(set(ab)))
    aw_s="".join(f"[{s}]" for s in sorted(set(aw)))
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

def is_white_dead(board, white_core):
    # white dead if core not present (captured) or group has 0 libs (should be captured) or eye check fails
    # For simple, captured = core not in board
    return to_pos(white_core) not in board

def find_snapback(center, white_rel, max_tries=5000):
    # center is sgf, white_rel is list of (dx,dy) offsets
    cx,cy=to_pos(center)
    aw_abs=[to_sgf(cx+dx, cy+dy) for dx,dy in white_rel]
    # candidate perimeter: all points within 3 steps
    all_pts=[]
    for x in range(cx-3,cx+4):
        for y in range(cy-3,cy+4):
            if 0<=x<19 and 0<=y<19:
                s=to_sgf(x,y)
                if s not in aw_abs:
                    all_pts.append(s)
    # brute choose black wall: we will iterate random subsets
    # For snapback we need at least one black single stone that can be captured
    # We'll brute force leave 2-3 empty points among neighbor ring
    # Determine neighbor ring (adjacent to white group)
    tmp=mkboard([], aw_abs)
    neigh=set()
    for s in aw_abs:
        for nb in neighbors(to_pos(s)):
            if nb not in tmp:
                neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    # outer ring
    outer=[s for s in all_pts if s not in neigh]
    random.seed(0)
    for _ in range(2000):
        # choose leave 2 among neigh
        leave = random.sample(neigh, 2)
        leave_set=set(leave)
        black_neigh=[s for s in neigh if s not in leave_set]
        # add ~8 outer stones randomly to make wall thick and unique
        outer_choice=random.sample(outer, min(10, len(outer)))
        ab=black_neigh+outer_choice
        ab=[s for s in ab if s not in aw_abs]
        b=mkboard(ab, aw_abs)
        if has_zero(b): continue
        # ensure white group has len(leave) libs
        try:
            g,l=group_libs(b, to_pos(aw_abs[0]))
        except: continue
        if len(l)!=len(leave): continue
        # test snapback: B plays throw-in at one leave, W captures, B recaptures kills
        # Need to detect capture sequence depth 3
        # Try both leave points as throw-in
        for throw in leave:
            other=leave[1] if leave[0]==throw else leave[0]
            # B throw
            b1,err=apply(b,'B',throw)
            if err: continue
            # White must capture (should capture something). Find W capture move: should be at other? Or capture throw stone?
            # In snapback, W captures throw stone by playing at adjacent point? Actually throw stone at throw, W captures by playing at other? Not necessarily.
            # For simple snapback, after B throw, white group gains a stone edge capture? Let's just brute all W replies that are captures
            # Find all possible W moves that are legal and capture at least one black stone
            found_w=None
            for wmv in leave+neigh+outer_choice:
                if wmv==throw: continue
                if to_pos(wmv) in b1: continue
                b2,err2=apply(b1,'W',wmv)
                if err2: continue
                # did W capture the throw stone?
                if to_pos(throw) not in b2 and to_pos(throw) in b1:
                    # W captured throw
                    found_w=wmv
                    break
            if not found_w: continue
            b2,_=apply(b1,'W',found_w)
            # Now B recaptures at throw or other?
            for bmv in [throw, other]:
                if to_pos(bmv) in b2: continue
                b3,err3=apply(b2,'B',bmv)
                if err3: continue
                if is_white_dead(b3, aw_abs[0]):
                    # kill achieved via 3-move snapback
                    # Check that alternative B first move (other) does NOT lead to dead even with best defense, and W can live
                    # Test B other immediate: if B plays other, white should not be dead after any W reply
                    b_alt,err_alt=apply(b,'B',other)
                    if err_alt: continue
                    if is_white_dead(b_alt, aw_abs[0]):
                        continue # other also kills -> not distinct
                    # Try to see if after B other, White can survive (has at least 2 libs)
                    # Simple: white still alive (core present) is enough for easy
                    # So we have distinct
                    return ab, aw_abs, throw, other, found_w, bmv
    return None

# Generate P1
res=find_snapback("nn", [(0,0),(1,0)])
print("P1 snap", res)
if res:
    ab,aw,throw,other,wcap,brec = res
    print(f"throw {throw} other {other} wcap {wcap} brec {brec}")
    # Build variations: correct line B throw W wcap B brec RIGHT; wrong line B other W wcap? Need refutation
    # Wrong line: B other, then W captures or lives. We'll include W throw as refutation (white captures or makes life)
    # For simplicity, wrong line = B other, W throw (or W wcap) shows white not dead
    vars=[
        ([("B",throw),("W",wcap),("B",brec)], True),
        ([("B",other),("W",throw)], False),
        ([("B",throw),("W",other)], False), # if W deviates
    ]
    # Also need to test legality of these lines
    def test_vars(ab,aw,vars):
        b=mkboard(ab,aw)
        for seq,right in vars:
            cur=dict(b)
            ok=True
            for c,coord in seq:
                nxt,err=apply(cur,c,coord)
                if err:
                    print(f" illegal {seq} {err}")
                    ok=False; break
                cur=nxt
            if ok:
                print(f" ok {seq} {'RIGHT' if right else 'wrong'} white dead? {is_white_dead(cur, aw[0])}")
        # Also need alternating check: seq starts with B, so alternates B,W,B etc. Our vars alternate correctly.
    test_vars(ab,aw,vars)
    sgf=sgf_str(ab,aw,vars)
    print(sgf)
    # Write with extra far stones to increase uniqueness per problem
    pathlib.Path("outputs/problem-01.sgf").write_text(sgf)

# Try different center for P2 White to kill (swap colors)
res2=find_snapback("jj", [(0,0),(1,0)])
print("P2", res2)
if res2:
    ab,aw,throw,other,wcap,brec = res2
    # swap colors: White is killer, so ab/aw swapped, and sequence colors swapped
    # Original res was Black killer vs White victim. For White killer, victim is Black.
    # So swap: new AB = aw, new AW = ab, and throw etc remain but colors invert
    # Sequence for White killer: W throw, B wcap, W brec
    vars2=[
        ([("W",throw),("B",wcap),("W",brec)], True),
        ([("W",other),("B",throw)], False),
    ]
    test_vars(aw,ab, [([("W",throw),("B",wcap),("W",brec)], True)])
    sgf2=sgf_str(aw,ab,vars2)
    pathlib.Path("outputs/problem-02.sgf").write_text(sgf2)
    print(sgf2)
