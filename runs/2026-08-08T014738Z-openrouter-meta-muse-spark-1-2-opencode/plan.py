from collections import deque

# Helper to visualize boards and test sequences quickly via mental but we do script
# We will design each problem board manually using coordinates
# Let's brute define 10 problems with careful positions

# Common utilities inline
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
    if p in board: return None,"occupied"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(g)
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suicide"
    return nb,None

def board_from(ab_list, aw_list):
    b={}
    for s in ab_list: b[to_pos(s)]='B'
    for s in aw_list: b[to_pos(s)]='W'
    return b

def check_setup(ab,aw):
    b=board_from(ab,aw)
    z=has_zero(b)
    if z: print(f"ZERO at {to_sgf(*z)} {b[z]}")
    else: print(f"OK {len(ab)}B {len(aw)}W")
    return b

# We'll craft problems interactively; this script is template for checking each
# Example: Problem1 test
ab=["jk","kj","lj","mk","jl","ll"]
aw=["kk","lk","kl"]
b=check_setup(ab,aw)
# Try B km
for mv in ["km","jm","lm","mm","kn"]:
    nb,err=apply(b,'B',mv)
    print(mv,err if err else "ok", end="; ")
    if nb:
        # check white reply km
        if mv!="km":
            nb2,err2=apply(nb,'W',"km")
            print(f"W km -> {err2}")
        else:
            print(f" -> live? libs {group_libs(nb,to_pos(mv))[1]}")
print()

# For problem2 etc we will expand below
