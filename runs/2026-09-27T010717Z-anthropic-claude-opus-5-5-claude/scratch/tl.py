"""Toolkit: problem specs, calling the C solver, tree verification."""
import subprocess, os, sys
from go import *

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, 'tsolve')
TIMEOUT = 3600

def col(c): return BLACK if c in ('B', 'b', BLACK) else WHITE

def rect(a, b):
    x0, y0 = ord(a[0]) - 97, ord(a[1]) - 97
    x1, y1 = ord(b[0]) - 97, ord(b[1]) - 97
    return [y * N + x for y in range(min(y0, y1), max(y0, y1) + 1) for x in range(min(x0, x1), max(x0, x1) + 1)]

class Spec:
    def __init__(self, AB, AW, region, solver, goal, key, strict=False, maxdepth=40, prune=True):
        self.AB = AB.split() if isinstance(AB, str) else list(AB)
        self.AW = AW.split() if isinstance(AW, str) else list(AW)
        if isinstance(region, str): region = region.split()
        pts = set()
        for r in region:
            if isinstance(r, int): pts.add(r)
            elif ':' in r:
                a, b = r.split(':'); pts.update(rect(a, b))
            else: pts.add(s2i(r))
        self.region = sorted(pts)
        self.solver = col(solver)
        self.goal = goal
        self.key = [s2i(k) for k in (key.split() if isinstance(key, str) else key)]
        self.strict = strict
        self.maxdepth = maxdepth
        self.prune = prune
    def board(self):
        bd = Board()
        for p in self.AB: bd.set(s2i(p), BLACK)
        for p in self.AW: bd.set(s2i(p), WHITE)
        return bd
    def with_(self, **kw):
        import copy
        s = copy.copy(self)
        for k, v in kw.items():
            if k == 'solver': v = col(v)
            if k == 'key': v = [s2i(x) for x in v.split()]
            setattr(s, k, v)
        return s

def run(spec, bd, tomove, ko=-1, lastpass=0, cmd='all', strict=None, solver=None, goal=None):
    sv = spec.solver if solver is None else solver
    gl = spec.goal if goal is None else goal
    st = spec.strict if strict is None else strict
    bs = ''.join('.XO'[v] for v in bd.b)
    inp = f"{sv} {gl} {int(st)} {spec.maxdepth} {int(spec.prune)}\n{len(spec.key)} {' '.join(map(str, spec.key))}\n" \
          f"{len(spec.region)} {' '.join(map(str, spec.region))}\n{bs}\n{tomove} {ko if ko is not None else -1} {lastpass}\n{cmd}\n"
    out = subprocess.run([EXE], input=inp, capture_output=True, text=True, timeout=TIMEOUT).stdout
    if cmd == 'value':
        p = out.split(); return p[1], int(p[2])
    res = {}
    for line in out.strip().split('\n'):
        p = line.split()
        if p[0] == 'pass': res['pass'] = (p[1], int(p[2]))
        else:
            if p[1] in ('I', 'K'): continue
            res[i2s(int(p[0]))] = (p[1], int(p[2]))
    return res

def status(spec, bd, tomove, ko=-1):
    """Classify position: solver unconditional win, opponent unconditional win, or neither (ko etc.)."""
    a, _ = run(spec, bd, tomove, ko, cmd='value')
    if a == 'W': return 'solver'
    other_goal = 'kill' if spec.goal == 'live' else 'live'
    b, _ = run(spec, bd, tomove, ko, cmd='value', solver=opp(spec.solver), goal=other_goal)
    if b == 'W': return 'opponent'
    return 'neither'

def apply(bd, mv, c):
    """Return (newboard, ko) or raise."""
    nb = bd.copy()
    i = s2i(mv)
    cap = nb.play(i, c)
    if cap is None: raise ValueError('illegal move %s' % mv)
    ko = -1
    if len(cap) == 1:
        st, lb = nb.chain(i)
        if len(st) == 1 and len(lb) == 1: ko = cap[0]
    return nb, ko

def spec_from_root(root, region, solver, goal, key, **kw):
    return Spec(root.props.get('AB', []), root.props.get('AW', []), region, solver, goal, key, **kw)

def verify(spec, root, verbose=True, full=True):
    """Walk tree and check leaves and completeness. Returns list of issues."""
    issues = []
    bd0 = spec.board()
    S = spec.solver
    stats = {'nodes': 0, 'maxlen': 0}
    def walk(node, bd, tomove, ko, path, onright):
        kids = node.children
        stats['nodes'] += 1
        stats['maxlen'] = max(stats['maxlen'], len(path))
        pstr = ' '.join(path) or '(root)'
        if not kids:
            c = node.props.get('C', [''])[0]
            right = 'RIGHT' in c
            st = status(spec, bd, tomove, ko)
            if right and st != 'solver':
                issues.append(f'RIGHT leaf not solver win: {pstr} -> {st}')
            if not right and st == 'solver':
                issues.append(f'WRONG leaf but solver wins: {pstr}')
            if not right and tomove != S:
                issues.append(f'note: wrong leaf ends on solver move: {pstr} ({st})')
            if right and tomove == S:
                issues.append(f'note: RIGHT leaf ends on opponent move: {pstr}')
            if verbose: print(f'  leaf {"RIGHT" if right else "wrong"} [{st}] {pstr}')
            return right
        anyright = False
        # compute analysis for this node
        if full:
            an = run(spec, bd, tomove, ko)
        else:
            an = None
        kidmoves = []
        childright = {}
        for ch in kids:
            m = ch.move()
            if m is None: issues.append(f'no move at node after {pstr}'); continue
            c, mv = m
            if col(c) != tomove: issues.append(f'wrong color {c}[{mv}] after {pstr}')
            try:
                nb, nko = apply(bd, mv, col(c))
            except ValueError as e:
                issues.append(f'{e} after {pstr}'); continue
            kidmoves.append(mv)
            r = walk(ch, nb, opp(col(c)), nko, path + [c + '[' + mv + ']'], onright)
            childright[mv] = r
            anyright = anyright or r
        if an is not None:
            if tomove == S:
                wins = sorted(m for m, v in an.items() if v[0] == 'W')
                for mv, r in childright.items():
                    v = an.get(mv, ('?', 0))[0]
                    if r and v != 'W': issues.append(f'accepted move {mv} not winning at {pstr} ({v})')
                    if not r and v == 'W': issues.append(f'move {mv} marked wrong but wins at {pstr}')
                missing = [m for m in wins if m not in childright]
                if missing and (anyright or not path):
                    issues.append(f'winning solver moves missing at {pstr}: {missing}')
                if verbose:
                    print(f'  solver node {pstr}: wins={wins}')
            else:
                loses = sorted(m for m, v in an.items() if v[0] != 'W')
                if anyright and loses:
                    issues.append(f'opponent refutes at {pstr}: {loses}')
                if anyright and verbose:
                    rs = sorted(((v[1], m) for m, v in an.items() if v[0] == 'W'), reverse=True)
                    print(f'  opp node {pstr}: resist(depth)={rs[:8]} covered={kidmoves}')
                if not anyright and verbose:
                    refs = sorted(m for m, v in an.items() if v[0] != 'W')
                    print(f'  opp node (wrong line) {pstr}: refutations={refs} covered={kidmoves}')
        return anyright
    walk(root, bd0, S, -1, [], True)
    if stats['maxlen'] > 14: issues.append(f"line too long {stats['maxlen']}")
    if stats['nodes'] > 121: issues.append(f"too many nodes {stats['nodes']}")
    if verbose:
        print('nodes', stats['nodes'] - 1, 'maxlen', stats['maxlen'])
        for i in issues: print('ISSUE', i)
    return issues

def mk(AB, AW, tree_text):
    """Build SGF text from setup and a tree string like '(;B[aa];W[bb]C[RIGHT])(...)'."""
    ab = ''.join('[' + p + ']' for p in AB)
    aw = ''.join('[' + p + ']' for p in AW)
    return f'(;GM[1]FF[4]CA[UTF-8]SZ[19]AB{ab}AW{aw}\n{tree_text})\n'

def diagram(text, origin='aa'):
    """Parse ASCII diagram. X/O stones, x/o stones inside region, '.' empty region,
    ',' or '-' empty outside region. Returns (AB, AW, region list)."""
    x0, y0 = ord(origin[0]) - 97, ord(origin[1]) - 97
    AB, AW, reg = [], [], []
    rows = [r.split() for r in text.strip('\n').split('\n') if r.strip()]
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            p = chr(97 + x0 + dx) + chr(97 + y0 + dy)
            if ch in 'Xx': AB.append(p)
            if ch in 'Oo': AW.append(p)
            if ch in '.xo': reg.append(p)
    return AB, AW, reg

def dspec(text, origin, solver, goal, key, **kw):
    AB, AW, reg = diagram(text, origin)
    return Spec(AB, AW, reg, solver, goal, key, **kw)

def explore(spec, moves=(), show_board=True):
    bd = spec.board(); c = spec.solver; ko = -1
    for mv in moves:
        bd, ko = apply(bd, mv, c); c = opp(c)
    if show_board: print(show(bd, set(spec.region)))
    an = run(spec, bd, c, ko)
    tag = 'solver' if c == spec.solver else 'opp'
    if c == spec.solver:
        print(tag, 'wins:', sorted((m, v[1]) for m, v in an.items() if v[0] == 'W'))
        print('   U:', sorted(m for m, v in an.items() if v[0] == 'U'))
    else:
        print(tag, 'refutes:', sorted((m, v[1]) for m, v in an.items() if v[0] != 'W'))
        print('   solver-wins-after (depth):', sorted(((v[1], m) for m, v in an.items() if v[0] == 'W'), reverse=True))
    return an

def clarity(spec, moves, verbose=True):
    """After `moves` (ending with a solver move), for each opponent reply count solver winning moves."""
    bd = spec.board(); c = spec.solver; ko = -1
    for mv in moves:
        bd, ko = apply(bd, mv, c); c = opp(c)
    assert c != spec.solver
    an = run(spec, bd, c, ko)
    res = []
    for m, v in an.items():
        if v[0] != 'W':
            res.append((m, 'REFUTES')); continue
        if m == 'pass':
            nb, nko = bd, -1
        else:
            nb, nko = apply(bd, m, c)
        a2 = run(spec, nb, opp(c), nko)
        wins = sorted(k for k, w in a2.items() if w[0] == 'W')
        res.append((m, len(wins), wins, v[1]))
    res.sort(key=lambda r: (r[1] if isinstance(r[1], int) else -1))
    if verbose:
        for r in res: print('   ', r)
    return res

def tpt(p, T):
    """Transform sgf point by symmetry T (0..7)."""
    x, y = ord(p[0]) - 97, ord(p[1]) - 97
    if T & 1: x = 18 - x
    if T & 2: y = 18 - y
    if T & 4: x, y = y, x
    return chr(97 + x) + chr(97 + y)

def tspec(sp, T):
    s = Spec([tpt(p, T) for p in sp.AB], [tpt(p, T) for p in sp.AW], [tpt(i2s(i), T) for i in sp.region],
             'B' if sp.solver == BLACK else 'W', sp.goal, [tpt(i2s(k), T) for k in sp.key], sp.strict, sp.maxdepth, sp.prune)
    return s

def ttree(text, T):
    import re
    return re.sub(r'([BW])\[([a-s][a-s])\]', lambda m: m.group(1) + '[' + tpt(m.group(2), T) + ']', text)
