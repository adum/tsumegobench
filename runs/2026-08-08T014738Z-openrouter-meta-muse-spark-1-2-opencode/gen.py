import random, re, itertools
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
    if p in board: return None, "occupied"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None, "suicide"
    return nb, None

# eye count helper crude
def eye_regions(board, color, center, radius=3):
    # count distinct empty regions that are fully surrounded by color+edge
    # simplified: for leaf evaluation we check capture instead
    pass

# Try generate P1 : simple kill by vital, depth 1
# brute create a 7x7 window at columns g-m rows g-m (around 6-12)
# place White 2-4 stones cluster in center, surround with Black leaving 1-2 empty vital points
# test

import pathlib

def generate_one(seed, target_difficulty):
    # fixed pattern to ensure uniqueness: use irregular outer wall
    # Use base at k10 region
    # White stones fixed L as before, Black wall with one hole
    # We'll define outer ring
    cx,cy=10,10 # k,k
    # Place White core 3 stones
    white_core = ["kk","lk","kl"]
    # Place Black ring candidates
    ring = ["kj","lj","mj","jk","mk","jl","ll","ml","jm","km","mm","jn","kn","ln"]
    # Choose subsets to leave vital(s)
    # For easy problem, leave 1 vital + 1 extra liberty so White has 2 liberties but only one makes 2 eyes
    # We'll brute choose which 2 to leave empty
    best=[]
    for leave in itertools.combinations(ring, 2):
        black = [p for p in ring if p not in leave]
        ab = black
        aw = white_core
        # also add outer support stones to give Black liberties so not in atari themselves
        # add extra Black far wall so Black group not self-atari
        extra_black = ["hj","ij","jj","nj","oj","hk","ok","hl","ol","hm","om","hn","on","ho","io","jo","no","oo"]
        # Only add some to keep <48 stones
        # For easy, just add a line at top/bottom to ensure Black alive
        ab2 = ab + ["jj","lj","nj","jk","mk","jn","kn"]  # duplicates okay
        # deduplicate
        ab2 = list(dict.fromkeys(ab2))
        # remove any overlap with aw or leave points
        ab2 = [p for p in ab2 if p not in aw and p not in leave]
        # Check illegal overlap
        b={}
        for s in ab2: b[to_pos(s)]='B'
        for s in aw: b[to_pos(s)]='W'
        if has_zero(b): continue
        # Try B moves: each empty in ring + center
        for mv in leave:
            nb,err=apply(b,'B',mv)
            if err: continue
            # after B move, check if White group dead (captured) or no eyes
            # If White stones still present, check liberties
            wpos = to_pos("kk")
            if wpos not in nb:
                # captured -> kill works
                # check other move alternative not killing
                other = leave[1] if leave[0]==mv else leave[0]
                nb2,err2=apply(b,'B',other)
                if err2: continue
                if to_pos("kk") in nb2:
                    # other move not capture -> good distinction
                    best.append((ab2,aw,mv,other))
                    break
        if best: break
    return best[:1]

res=generate_one(0, "easy")
print(res)
if res:
    ab,aw,mv,other=res[0]
    print(f"AB {ab} AW {aw} vital {mv} other {other}")
    # Build sgf
    ab_str="".join(f"[{x}]" for x in ab)
    aw_str="".join(f"[{x}]" for x in aw)
    sgf=f"(;SZ[19]AB{ab_str}AW{aw_str}(;B[{mv}]C[RIGHT])(;B[{other}];W[{mv}]))"
    pathlib.Path("/tmp/test_p1.sgf").write_text(sgf)
    print(sgf)
    # verify with has_zero etc
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    nb,_=apply(b,'B',mv)
    print("After vital White present?", to_pos("kk") in nb)
    for p in list(nb):
        if p not in set([to_pos(s) for s in ab+aw]+[to_pos(mv)]):
            continue
    print("lib after vital", group_libs(nb,to_pos(mv)) if to_pos(mv) in nb else "n/a")
