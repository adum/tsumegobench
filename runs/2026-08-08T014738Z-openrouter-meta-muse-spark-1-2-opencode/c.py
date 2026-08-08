import pathlib, json, re, sys, os, time
# quick validate problem-01
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
    if p in board: return None,"occupied "+coord
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suicide "+coord
    return nb,None
def check(p):
    txt=pathlib.Path(p).read_text()
    ab=set()
    aw=set()
    for m in re.finditer(r'AB((?:\[[a-s]{2}\])+)', txt):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): ab.add(mm.group(1))
    for m in re.finditer(r'AW((?:\[[a-s]{2}\])+)', txt):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): aw.add(mm.group(1))
    print("AB",len(ab),"AW",len(aw),"overlap",ab&aw)
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    z=has_zero(b)
    print("zero?", z)
    if z: print(to_sgf(*z), b[z])
    # check root C
    fm=min([x for x in [txt.find(";B["), txt.find(";W[")] if x!=-1]+[len(txt)])
    print("root C?", "C[" in txt[:fm])
    print("RIGHT?", "RIGHT" in txt)
    # check moves alternating / legality via simple DFS parse
    # Use regex sequence extraction per variation? Let's brute follow all paths via SGF tree parser simple
    # Instead just test given lines
    tests=[["op"],["or","op"],["qq","op"],["mn","op"],["aa","op"]]
    # But we need color alternation: those are B then W
    for seq in tests:
        cur=dict(b)
        cols=["B","W","B","W","B"]
        # For this file, first B, second W etc. For single move, just B
        for i,coord in enumerate(seq):
            col=cols[i]
            nxt,err=apply(cur,col,coord)
            if err:
                print(f" seq {seq} fail at {col}[{coord}] {err}")
                break
            cur=nxt
        else:
            print(f" seq {seq} ok white left {sum(1 for v in cur.values() if v=='W')}")
check("outputs/problem-01.sgf")
