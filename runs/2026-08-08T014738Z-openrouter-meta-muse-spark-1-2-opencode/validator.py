import re

def parse_setup(sgf):
    ab=set()
    aw=set()
    for m in re.finditer(r'AB((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)):
            ab.add(mm.group(1))
    for m in re.finditer(r'AW((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)):
            aw.add(mm.group(1))
    return ab, aw

def to_pos(s): return (ord(s[0])-97, ord(s[1])-97)
def to_sgf(x,y): return chr(97+x)+chr(97+y)

def make_board(ab, aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b

def neighbors(p):
    x,y=p
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny=x+dx,y+dy
        if 0<=nx<19 and 0<=ny<19: yield (nx,ny)

def group_libs(board, start):
    col=board[start]
    vis=set([start]); stack=[start]; libs=set()
    while stack:
        cur=stack.pop()
        for nb in neighbors(cur):
            if nb not in board: libs.add(nb)
            elif board[nb]==col and nb not in vis:
                vis.add(nb); stack.append(nb)
    return vis, libs

def has_zero_lib(board):
    seen=set()
    for p in board:
        if p in seen: continue
        g,l=group_libs(board,p)
        seen|=g
        if len(l)==0: return p
    return None

def apply(board, color, sgf_coord):
    p=to_pos(sgf_coord)
    if p in board: return None,"occupied"
    nb=dict(board); nb[p]=color
    opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(g)
    for c in caps: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suicide"
    return nb,None

def check_file(path):
    import pathlib
    sgf=pathlib.Path(path).read_text()
    ab,aw=parse_setup(sgf)
    overlap=ab&aw
    if overlap: print("overlap",overlap)
    board=make_board(ab,aw)
    z=has_zero_lib(board)
    if z: print(f"{path}: zero liberty at {to_sgf(*z)} color {board[z]}")
    else: print(f"{path}: setup ok {len(ab)}B {len(aw)}W")
    print(" SZ", "SZ[19]" in sgf, " RIGHT", "RIGHT" in sgf)
    # check root C
    # root is up to first ;B or ;W after initial (
    idx=sgf.find(";B[")
    idx2=sgf.find(";W[")
    first_move=min(x for x in [idx,idx2] if x!=-1) if idx!=-1 or idx2!=-1 else len(sgf)
    root=sgf[:first_move]
    if "C[" in root: print("  ROOT HAS C -> invalid")
    # check each variation branch for legality using simple recursive parser
    # We'll parse SGF tree structure: tokenize
    import re
    # quick check: every node after root has exactly one B or W
    # count nodes: split on '(' and ';'
    # Use stack for variations
    # For now just check occupancy/suicide along depth-first path extraction via recursion
    def parse_sgf_tree(s):
        # returns tree as nested list of nodes; simplified: use recursion on parentheses
        # We'll walk char by char
        stack=[]
        cur=[]
        i=0
        # Better: extract all sequences between '(' and ')'
        # Instead do direct validation: walk SGF and simulate board along each path using branching
        paths=[]
        def dfs(pos, board_state, color_turn):
            # pos index in sgf string
            pass
        return
    return board

def check_sgf(sgf):
    ab,aw=parse_setup(sgf)
    overlap=ab&aw
    if overlap: print("overlap",overlap)
    board=make_board(ab,aw)
    z=has_zero_lib(board)
    if z: print("zero liberty at",to_sgf(*z))
    else: print("setup ok",len(ab),len(aw))
    # find all B[xx] W[xx] moves in order? Check alternating? Just check occupied/suicide through variations tree is harder
    # extract all move coords
    moves=re.findall(r';[BW]\[([a-s]{2})\]',sgf)
    print("moves sample",moves[:10])
    # check SZ, AB, AW, no root C, no root move
    print("SZ", "SZ[19]" in sgf)
    print("AB", "AB" in sgf, "AW", "AW" in sgf)
    # root check
    root_part=sgf.split(";")[0]
    print("root has C?", "C[" in root_part)
    print("has RIGHT", "RIGHT" in sgf)
    # check alternating on each line? parse tree: we just check main line ok via applying sequentially
    # Simple test: apply first few moves linearly ignoring branches (take first occurrence order)
    b=board
    col=None
    # find sequence of first branch: extract nodes in order as they appear nested? Use regex for ;B[xx] ;W[xx] sequence along first variation path (rough)
    seq=re.findall(r';([BW])\[([a-s]{2})\]',sgf)
    if seq:
        first_color=seq[0][0]
        print("first player",first_color)
        for i,(c,coord) in enumerate(seq):
            # only follow first branch linear? but sgf branching interleaves; seq gives depth-first order which not linear
            pass
    # better: walk SGF tree? Skip for now
    return board

# test will be done per file
