import itertools, re, pathlib

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
    if p in board: return None,"occup"
    nb=dict(board); nb[p]=color; opp='W' if color=='B' else 'B'
    caps=[]
    for n in neighbors(p):
        if n in nb and nb[n]==opp:
            g,l=group_libs(nb,n)
            if len(l)==0: caps.extend(list(g))
    for c in caps:
        if c in nb: del nb[c]
    g,l=group_libs(nb,p)
    if len(l)==0: return None,"suici"
    return nb,None
def mkboard(ab,aw):
    b={}
    for s in ab: b[to_pos(s)]='B'
    for s in aw: b[to_pos(s)]='W'
    return b
def white_alive(board, white_core_pos):
    # check if white group containing core still present and has >=2 liberties or not captured
    # For kill problem, white dead if not on board
    if white_core_pos not in board: return False
    # check liberties crude: if has 1 liberty maybe still alive if eye? we treat capture as only death for easy
    return True

# Generator for easy kill: immediate capture
# Choose center (10,10) = kk
# White stones: 2 stones at kk, lk (horizontal 2)
# Surrounding empties: we need positions where playing captures
# White group liberties currently: all adjacent empties
# Let's compute white liberties in empty surrounding and test capture

def find_easy_kill():
    white_core = ["kk","lk"]
    # define candidate empty area: ring around kk/lk
    # White group occupies kk(10,10) lk(11,10)
    # Its direct neighbors: kj(10,9), lj(11,9), km(10,11), lm(11,11), jk(9,10), mk(12,10), etc.
    # Black must occupy most liberties leaving exactly 2 liberties, one is capturing (filling last liberty after White has 1)
    # But if White has 2 liberties, Black playing one reduces to 1, not capture. Need White to have 1 liberty already? Then Black capture.
    # Actually capture occurs when Black plays last liberty.
    # So design: White has 2 liberties, but one liberty is shared and playing there captures immediately due to surround? Need Wall.
    # Simpler: Surround White group completely except 1-2 points, so White group has 1-2 libs.
    # Black plays last liberty captures.
    ring_all = ["jk","kk","lk","mk","ij","kj","lj","mj","ii","ki","li","mi","ih","kh","lh","mh","ik","jk","kk","lk","mk","il","kl","ml","im","km","mm","in","kn","ln","jo","ko","lo","jj","kj","lj","mj"] # messy duplicates
    # Let's define explicitly set of coordinates within 2 steps of core
    core_pos=[to_pos(s) for s in white_core]
    cand=set()
    for x in range(8,14):
        for y in range(8,13):
            cand.add(to_sgf(x,y))
    cand=list(cand)
    # brute choose black wall that leaves exactly 2 empty points among neighbors of white
    neigh=set()
    wboard={}
    for s in white_core: wboard[to_pos(s)]='W'
    for p in list(wboard.keys()):
        for nb in neighbors(p):
            if nb not in wboard: neigh.add(to_sgf(*nb))
    neigh=list(neigh)
    print("neigh",neigh)
    # try leaving 2 libs
    for leave in itertools.combinations(neigh, 2):
        # black occupies all other neigh plus extra outer support
        black=list(set(neigh) - set(leave))
        # add outer reinforcement so black not weak: add second ring
        extra=[]
        for x in range(7,14):
            for y in range(7,13):
                s=to_sgf(x,y)
                if s not in white_core and s not in leave and s not in black:
                    # add some perimeter stones at distance 2
                    if abs(x-10)>=2 or abs(y-10)>=2:
                        # add maybe all distance 2 ring fully occupied to make wall thick
                        extra.append(s)
        # limit total stones to <30
        extra=extra[:10]
        ab=black+extra
        # remove duplicates overlapping white
        ab=[s for s in ab if s not in white_core]
        ab=list(dict.fromkeys(ab))
        # check overlapping and zero libs
        if len(ab)>35: continue
        b=mkboard(ab,white_core)
        if has_zero(b): continue
        # ensure white has exactly len(leave) liberties
        # count libs of white group
        g,l=group_libs(b, to_pos(white_core[0]))
        if len(l)!=len(leave): continue
        # try each leave as killing move
        kill=None; fail=None
        for mv in leave:
            nb,err=apply(b,'B',mv)
            if err: continue
            if to_pos(white_core[0]) not in nb:
                # capture -> kill candidate
                if kill is None: kill=mv
            else:
                # not capture -> fail candidate
                # also check if fail move still leaves white alive (not suicide for black)
                fail=mv
        if kill and fail:
            # distinct kill vs fail
            # also verify fail move is not also capturing via different order (we already)
            # verify wrong move refutation: White can survive (still on board)
            nb2,_=apply(b,'B',fail)
            if to_pos(white_core[0]) in nb2:
                return ab, white_core, kill, fail, b
    return None

res=find_easy_kill()
print(res)
if res:
    ab,aw,kill,fail,b=res
    print(f"AB {ab}\nAW {aw}\nkill {kill} fail {fail}")
    # build sgf for easy: 1 right, 1 wrong refuted by staying alive (no extra move needed maybe white replies)
    # Wrong line ends after white not captured - need show refutation: after fail, white still alive, so we need end at fail? But spec says wrong line ends on opponent's refuting move. If fail just doesn't kill, that's not refutation yet. Need to show white survives. However for atari capture kill, wrong move simply doesn't capture, so failure is immediate: white still alive with 1 liberty but not captured. Is that "forced and clear"? Perhaps need to add W move that shows survival? For easy capture, wrong move leaves white with 1 liberty but Black could still capture next move, so not yet failure. So need to pick leave points such that after fail move, White can capture back or make life.
    # Better to require fail leads to White still having 2 liberties, not immediate death.
    # Our simple model may need extra depth.
    # Let's output sgf anyway
    ab_s="".join(f"[{s}]" for s in ab)
    aw_s="".join(f"[{s}]" for s in aw)
    sgf=f"(;SZ[19]AB{ab_s}AW{aw_s}(;B[{kill}]C[RIGHT])(;B[{fail}];W[{kill}]))"
    print(sgf)
    pathlib.Path("tmp_gen_easy.sgf").write_text(sgf)
