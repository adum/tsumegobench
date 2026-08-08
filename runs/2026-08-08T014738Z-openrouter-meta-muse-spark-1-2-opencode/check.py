import pathlib, re, sys
# lets just brute check all outputs exist and are valid via simple rules

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
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

def check_path(path):
    import re
    sgf=pathlib.Path(path).read_text()
    print("===",path)
    print("RIGHT", "RIGHT" in sgf, "SZ19", "SZ[19]" in sgf)
    # basic AB AW
    ab=set(re.findall(r'AB\[([a-s]{2})\]', sgf))
    # Actually AB[aa][bb] style: need to find all
    ab2=set()
    for m in re.finditer(r'AB((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): ab2.add(mm.group(1))
    aw2=set()
    for m in re.finditer(r'AW((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): aw2.add(mm.group(1))
    if ab2 & aw2: print(" overlap", ab2&aw2)
    board={}
    for s in ab2: board[to_pos(s)]='B'
    for s in aw2: board[to_pos(s)]='W'
    # zero lib
    seen=set()
    bad=False
    for p in list(board):
        if p in seen: continue
        g,l=group_libs(board,p)
        seen|=g
        if len(l)==0:
            print(f" zero lib at {chr(97+p[0])+chr(97+p[1])} {board[p]}")
            bad=True
    if not bad: print(f" setup ok {len(ab2)}B {len(aw2)}W")
    # first move color consistency
    colors=re.findall(r';([BW])\[', sgf)
    print(" colors seq start", colors[:6])
    # check root C
    idxs=[x for x in [sgf.find(";B["), sgf.find(";W[")] if x!=-1]
    first=min(idxs) if idxs else len(sgf)
    if "C[" in sgf[:first]: print(" ROOT C!")
