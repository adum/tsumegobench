import pathlib, re, json, sys, os
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

def check_setup(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    if set(ab)&set(aw):
        print("overlap", set(ab)&set(aw))
        return None
    z=has_zero(b)
    if z:
        print(f" ZERO {to_sgf(*z)} {b[z]}")
        return None
    print(f" OK {len(ab)}B {len(aw)}W")
    return b

# TEST Problem 01 design attempt: Black to live, White surrounding
# Let's design a center problem where B has a 4-point shape with defect
print("=== P01 idea ===")
ab = ["jj","kj","lj","jk","kk","lk","jl"]
aw = ["ij","hj","jj","kj","lj","mj","ii","ki","li","ih","kh","lh","jm","km","mm"]
# this overlaps etc. Let's think differently: use validator approach interactive

# Instead let's brute attempt to create a simple but legal shape for kill
# Black group in atari needing one move, white to kill
# Example: White encircles black chain with 2 liberties, kill by playing vital
ab = ["jj","kj","lj","jk","lk"]
aw = ["ij","hj","jj","kj","ik","kk","lk","mk","il","kl","ml","jm","km","mm","jn","kn","ln"]
# too messy

# Let's design systematically small shapes by manual reasoning and then verify

def show(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    xs=[to_pos(s)[0] for s in ab+aw]
    ys=[to_pos(s)[1] for s in ab+aw]
    xmin=max(0,min(xs)-2); xmax=min(18,max(xs)+2)
    ymin=max(0,min(ys)-2); ymax=min(18,max(ys)+2)
    for y in range(ymin,ymax+1):
        row=""
        for x in range(xmin,xmax+1):
            if (x,y) in b: row+=b[(x,y)]
            else: row+="."
        print(f"{to_sgf(xmin,y)[1]} {row}")
    print("   "+"".join(to_sgf(x,0)[0] for x in range(xmin,xmax+1)))

# Let's attempt concrete P01: Edge shape, black to live by playing descent
# Board coordinates: use near top edge for visibility
# Let's use edge top: y=0 is top? In SGF, 'a' is top-left? Actually 'aa' is top-left. We'll use y small for top.
# Place black stones: wall on left and center, white stones around
ab = ["kc","lc","mc","kb","lb","mb","kd","ld","md"]
aw = ["jb","nb","jc","nc","jd","nd","je","ke","le","me","ne","kf","lf","mf"]
# This is rectangular block.
b=check_setup(ab,aw)
show(ab,aw)
# Try moves: maybe B kc etc. Not good.

# Let's use known working shape from reference but modify
# Instead copy logic from simple kill: black group with one eye at corner, white kills by vital
# Try sgf variation: start with simple L shape
print("\n=== L shape test ===")
ab = ["cc","dc","ec","cd","ed"]  # black stones forming bottom wall
aw = ["cb","db","eb","bc","cc","dc","ec","bd","dd","fd","be","ce","de","ee","fe"]
# overlaps - discard

# Quick approach: use existing example gp-18843 shape but shift and add stones to make original
# Let's just attempt to produce files via SGF templates that are verified legal via script brute
# We'll make 10 random but still life-and-death via simple atari capture

# For now test a super simple live shape: black group has 2 libs, white to move kills
ab = ["jj","kj","jk","kk"]
aw = ["ij","hj","jj","kj","lj","mj","ii","ki","li","ih","jh","kh","lh","mh","im","jm","km","lm","mm","jn","kn","ln","jo","ko","lo"]
print("\n=== simple encircle ===")
b=check_setup(ab,aw)
if b:
    show(ab,aw)
    # test vital
    for mv in ["kk","jj","jk","kk"]:
        pass
