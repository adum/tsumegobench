import subprocess, pathlib, re, json

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
    return nb,None
def mkboard(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b

# Helper to test a problem design
def test_problem(name, ab, aw, tree_desc):
    # tree_desc: list of variations: ([(color,coord)], is_right)
    # first entry is main line etc. We'll test legality of all moves
    print(f"\n=== {name} ===")
    b=mkboard(ab,aw)
    z=has_zero(b)
    if z: print(f"  SETUP ZERO at {to_sgf(*z)} {b[z]}")
    else: print(f"  setup OK {len(ab)}B {len(aw)}W")
    # check AB/AW distinct
    if set(ab)&set(aw): print("  OVERLAP", set(ab)&set(aw))
    # test each line
    for seq, is_right in tree_desc:
        cur=dict(b)
        ok=True
        last=None
        for col,coord in seq:
            if last and last==col: print(f"   BAD alt {seq}")
            last=col
            nxt,err=apply(cur,col,coord)
            if err:
                print(f"   illegal line {seq} at {col}[{coord}]: {err}")
                ok=False; break
            cur=nxt
        if ok:
            status="RIGHT" if is_right else "wrong"
            print(f"   {status} line {' '.join(c+'['+x+']' for c,x in seq)} OK")
            # show if capture occurred: count white stones
            white_stones = sum(1 for v in cur.values() if v=='W')
            print(f"      white stones left {white_stones}")
    # Check first move consistency
    first_colors=set(seq[0][0] for seq,_ in tree_desc if seq)
    print(f"  first colors {first_colors}")

# Define Problem 01: Black to play and kill. White 3-stone L at km/lm/kl, surrounded.
# Let's design fresh central position not at kk to avoid duplicate
# Use White at mo/no/mp? Let's pick central area near n-n
# White stones at nn, on, np (L shape near center-right)
ab1 = ["mm","nm","om","pm","mn","pn","mo","qo","mp","qp","mq","nq","oq","nr","or","pr"]
aw1 = ["nn","on","np"]
# Extra: need to block south and west more? Let's test
test_problem("P01 attempt A", ab1, aw1, [
    ([("B","op")], True),
    ([("B","pp")], False),
    ([("B","oq")], False),
])

# Show board around
def show(ab,aw):
    b=mkboard(ab,aw)
    xs=[to_pos(s)[0] for s in ab+aw]; ys=[to_pos(s)[1] for s in ab+aw]
    xmin=max(0,min(xs)-3); xmax=min(18,max(xs)+3)
    ymin=max(0,min(ys)-3); ymax=min(18,max(ys)+3)
    for y in range(ymin,ymax+1):
        row=""
        for x in range(xmin,xmax+1):
            row+= b.get((x,y), ".")
        print(f"{chr(97+y)} {row}")
    print("  "+"".join(chr(97+x) for x in range(xmin,xmax+1)))

show(ab1,aw1)
