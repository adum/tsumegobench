import re, pathlib, sys

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
def apply(board, color, sgf_coord):
    p=to_pos(sgf_coord)
    if p in board: return None,"occupied "+sgf_coord
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suicide "+sgf_coord
    return nb,None

def parse_setup(sgf):
    ab=set(); aw=set()
    for m in re.finditer(r'AB((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): ab.add(mm.group(1))
    for m in re.finditer(r'AW((?:\[[a-s]{2}\])+)', sgf):
        for mm in re.finditer(r'\[([a-s]{2})\]', m.group(1)): aw.add(mm.group(1))
    return ab,aw

def parse_sgf_paths(sgf):
    # Build tree: recursive descent parsing '(' ')' and ';' nodes
    # Each node is dict with props
    # We will generate all paths as list of (color,coord,comment)
    # Use stack of board states
    # Simplified: tokenize
    # Approach: parse into tree structure using index pointer
    n=len(sgf)
    def parse_collection(i):
        assert sgf[i]=='('
        i+=1
        # Expect ';' root
        nodes, i = parse_sequence(i)
        # Expect ')'
        # may have more variations at same level? Actually collection is sequence with branches
        # But top-level after root sequence we have variations (...)(...)...
        # Our parse_sequence will handle branches
        assert sgf[i]==')', f"expected ) at {i} got {sgf[i:i+10]}"
        i+=1
        return nodes, i
    def parse_sequence(i):
        seq=[]
        while i<n:
            c=sgf[i]
            if c==';':
                node, i = parse_node(i)
                seq.append(node)
            elif c=='(':
                # variation branch: contains a sequence (which may itself have branches)
                # The branch attaches to previous node
                # We store as child sequences of last node
                branch, i = parse_collection(i) # but collection expects '(' then sequence then ')', which matches variation '(' ';' ... ')'
                # Actually variation is '(' sequence ')'
                # parse_collection handles '(' ... ')'
                # Need to adjust: we called parse_collection which expects '(' at i; we are at '(' so it will parse one variation
                # Attach to last node
                if not seq:
                    raise ValueError("branch without preceding node")
                if '_branches' not in seq[-1]:
                    seq[-1]['_branches']=[]
                seq[-1]['_branches'].append(branch)
            elif c==')':
                break
            elif c in ' \n\r\t':
                i+=1
            else:
                i+=1
        return seq, i
    def parse_node(i):
        assert sgf[i]==';'
        i+=1
        props={}
        comments=[]
        while i<n and sgf[i] not in '();':
            # prop name
            m=re.match(r'[A-Z]+', sgf[i:])
            if not m: 
                i+=1; continue
            name=m.group(0); i+=len(name)
            vals=[]
            while i<n and sgf[i]=='[':
                end=sgf.find(']', i)
                if end==-1: raise ValueError("unclosed [")
                vals.append(sgf[i+1:end])
                i=end+1
            props[name]=vals
        return props, i
    tree, _ = parse_sequence(0)
    # tree is list of nodes at top level? Should be root + maybe? For normal SGF, first node is root, rest is main line
    # But due to parsing, root is first node, subsequent nodes are linear until branching
    return tree

def validate_file(path):
    sgf=pathlib.Path(path).read_text()
    print("===",path)
    # basic checks
    if "SZ[19]" not in sgf: print(" BAD SZ")
    if "AB" not in sgf or "AW" not in sgf: print(" BAD AB/AW")
    # root C
    first_move_idx=min([x for x in [sgf.find(";B["), sgf.find(";W[")] if x!=-1]+[len(sgf)])
    root=sgf[:first_move_idx]
    if "C[" in root: print(" BAD root C")
    if "RIGHT" not in sgf: print(" BAD no RIGHT")
    ab,aw=parse_setup(sgf)
    if ab & aw: print(" BAD overlap",ab&aw)
    board={}
    for s in ab: board[to_pos(s)]='B'
    for s in aw: board[to_pos(s)]='W'
    z=has_zero(board)
    if z: print(f" BAD zero liberty at {to_sgf(*z)}")
    else: print(f" setup ok {len(ab)}B {len(aw)}W")
    # parse tree and validate all paths
    try:
        tree=parse_sgf_paths(sgf)
    except Exception as e:
        print(" parse error",e)
        import traceback; traceback.print_exc()
        return
    # tree is flat list with branches attached
    # DFS to validate moves
    def dfs(seq, board_state, last_color, depth):
        # seq is list of nodes in order
        cur_board=board_state
        cur_color=last_color
        for idx, node in enumerate(seq):
            # node may have B or W
            move_color=None
            move_coord=None
            if 'B' in node: move_color='B'; move_coord=node['B'][0]
            elif 'W' in node: move_color='W'; move_coord=node['W'][0]
            else:
                # root node: no move
                # check branches attached to this node
                if '_branches' in node:
                    for br in node['_branches']:
                        dfs(br, cur_board, cur_color, depth)
                continue
            # check pass
            if move_coord=="": print(f" BAD pass at depth {depth}")
            # check alternating
            if cur_color and move_color==cur_color: print(f" BAD not alternating at {to_sgf(*to_pos(move_coord)) if len(move_coord)==2 else move_coord} depth {depth}")
            # check occupied/suicide
            nb, err = apply(cur_board, move_color, move_coord)
            if err: print(f" BAD illegal {err} at depth {depth} move {move_color}[{move_coord}]")
            else: cur_board=nb
            cur_color=move_color
            # check branches attached to this node - they start from this board state
            if '_branches' in node:
                for br in node['_branches']:
                    dfs(br, cur_board, cur_color, depth+1)
            # continue linear sequence with updated board
        # print leaf
    # The tree includes root as first element, so we start
    dfs(tree, board, None, 0)
    # check first move consistency
    # find all first moves (children of the last node before branching or root?)
    # Simpler: find all B[xx] W[xx] directly after root
    # In tree structure, variations are attached to last linear node; for typical SGF root with branches, root branches are first element's branches or second?
    # Let's extract first player
    first_colors=set()
    def collect_first(node_list):
        for node in node_list:
            if 'B' in node or 'W' in node:
                c='B' if 'B' in node else 'W'
                first_colors.add(c)
                break
            if '_branches' in node:
                for br in node['_branches']:
                    collect_first(br)
    # Instead use regex for colors after root: all occurrences of ;B[ or ;W[ at depth 1
    # Find position of root branches: look at tree[0] branches
    if tree and '_branches' in tree[0]:
        # root has branches directly
        for br in tree[0]['_branches']:
            for nd in br:
                if 'B' in nd: first_colors.add('B'); break
                if 'W' in nd: first_colors.add('W'); break
    elif len(tree)>1:
        # linear main line: first move is tree[1]
        if 'B' in tree[1]: first_colors.add('B')
        if 'W' in tree[1]: first_colors.add('W')
        # also branches off tree[1]
        if '_branches' in tree[1]:
            for br in tree[1]['_branches']:
                for nd in br:
                    if 'B' in nd: first_colors.add('B'); break
                    if 'W' in nd: first_colors.add('W'); break
    print(" first colors",first_colors)
    if len(first_colors)>1: print(" BAD inconsistent first player")
    # count nodes and max depth
    max_depth=0; node_count=0
    def count(seq, depth):
        nonlocal max_depth, node_count
        for node in seq:
            if 'B' in node or 'W' in node:
                node_count+=1
                max_depth=max(max_depth, depth)
                # depth increments per move? We'll compute path length
            if '_branches' in node:
                for br in node['_branches']:
                    count(br, depth+1)
            # linear next node depth+1?
            # For simplicity, treat sequence as linear path length
        # For accurate max line length, do DFS path walk separately
    # Do path DFS for depth
    def path_dfs(seq, board_state, last_color, length):
        nonlocal max_depth, node_count
        cur_board=board_state
        cur_len=length
        cur_color=last_color
        for node in seq:
            if 'B' in node or 'W' in node:
                c='B' if 'B' in node else 'W'
                coord=node[c][0]
                nb,err=apply(cur_board,c,coord)
                if not err: cur_board=nb
                cur_color=c
                cur_len+=1
                max_depth=max(max_depth, cur_len)
                if '_branches' in node:
                    for br in node['_branches']:
                        path_dfs(br, cur_board, cur_color, cur_len)
            else:
                if '_branches' in node:
                    for br in node['_branches']:
                        path_dfs(br, cur_board, cur_color, cur_len)
    path_dfs(tree, board, None, 0)
    print(f" total nodes ~{node_count} max_line {max_depth}")
    # count RIGHT leaves
    rights=sgf.count("RIGHT")
    print(f" RIGHT count {rights}")

for p in sys.argv[1:]:
    validate_file(p)
