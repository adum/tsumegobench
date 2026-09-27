"""Go helpers: board rules, SGF parse/write, ctypes bridge to C solver, tree validator."""
import ctypes
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
N = 19
EMPTY, BLACK, WHITE = 0, 1, 2
CNAME = {BLACK: 'B', WHITE: 'W'}


def opp(c):
    return 3 - c


def sgf2i(s):
    return (ord(s[1]) - 97) * N + (ord(s[0]) - 97)


def i2sgf(i):
    return chr(97 + i % N) + chr(97 + i // N)


def i2xy(i):
    return i % N, i // N


def xy2i(x, y):
    return y * N + x


def neighbors(i):
    x, y = i % N, i // N
    if x > 0:
        yield i - 1
    if x < N - 1:
        yield i + 1
    if y > 0:
        yield i - N
    if y < N - 1:
        yield i + N


class IllegalMove(Exception):
    pass


class Board:
    def __init__(self, stones=None):
        self.b = [EMPTY] * (N * N)
        self.ko = None  # point banned for side to move
        if stones:
            for i, c in stones.items():
                self.b[i] = c

    def copy(self):
        nb = Board()
        nb.b = self.b[:]
        nb.ko = self.ko
        return nb

    def chain(self, i):
        c = self.b[i]
        stones = {i}
        libs = set()
        stack = [i]
        while stack:
            p = stack.pop()
            for q in neighbors(p):
                if self.b[q] == c and q not in stones:
                    stones.add(q)
                    stack.append(q)
                elif self.b[q] == EMPTY:
                    libs.add(q)
        return stones, libs

    def play(self, i, c):
        """Play move; returns list of captured points. Raises IllegalMove."""
        if self.b[i] != EMPTY:
            raise IllegalMove('occupied %s' % i2sgf(i))
        if self.ko is not None and i == self.ko:
            raise IllegalMove('ko ban %s' % i2sgf(i))
        self.b[i] = c
        captured = []
        for q in neighbors(i):
            if self.b[q] == opp(c):
                st, lb = self.chain(q)
                if not lb:
                    for s in st:
                        self.b[s] = EMPTY
                    captured.extend(st)
        st, lb = self.chain(i)
        if not lb:
            self.b[i] = EMPTY
            for s in captured:
                self.b[s] = opp(c)
            raise IllegalMove('suicide %s' % i2sgf(i))
        if len(captured) == 1 and len(st) == 1 and len(lb) == 1:
            self.ko = captured[0]
        else:
            self.ko = None
        return captured

    def show(self, x0=0, y0=0, x1=18, y1=18, marks=None):
        marks = marks or {}
        lines = []
        cols = 'ABCDEFGHJKLMNOPQRST'
        lines.append('    ' + ' '.join(chr(97 + x) for x in range(x0, x1 + 1)))
        for y in range(y0, y1 + 1):
            row = []
            for x in range(x0, x1 + 1):
                i = xy2i(x, y)
                if i in marks:
                    row.append(marks[i])
                else:
                    row.append({EMPTY: '.', BLACK: 'X', WHITE: 'O'}[self.b[i]])
            lines.append('%s%2d %s' % (chr(97 + y), 19 - y, ' '.join(row)))
        return '\n'.join(lines)


# ---------------------------------------------------------------- SGF
class Node:
    def __init__(self, props=None):
        self.props = props or {}
        self.children = []

    def move(self):
        for k in ('B', 'W'):
            if k in self.props:
                return (BLACK if k == 'B' else WHITE, self.props[k][0])
        return None

    def comment(self):
        return ''.join(self.props.get('C', []))


def parse_sgf(text):
    pos = 0
    text = text.strip()

    def skip_ws():
        nonlocal pos
        while pos < len(text) and text[pos] in ' \t\r\n':
            pos += 1

    def parse_value():
        nonlocal pos
        assert text[pos] == '['
        pos += 1
        out = []
        while text[pos] != ']':
            if text[pos] == '\\':
                pos += 1
            out.append(text[pos])
            pos += 1
        pos += 1
        return ''.join(out)

    def parse_node():
        nonlocal pos
        assert text[pos] == ';'
        pos += 1
        props = {}
        skip_ws()
        while pos < len(text) and text[pos].isalpha():
            m = re.match(r'[A-Za-z]+', text[pos:])
            key = m.group(0)
            pos += len(key)
            skip_ws()
            vals = []
            while pos < len(text) and text[pos] == '[':
                vals.append(parse_value())
                skip_ws()
            props.setdefault(key, []).extend(vals)
            skip_ws()
        return Node(props)

    def parse_tree():
        nonlocal pos
        skip_ws()
        assert text[pos] == '(', text[pos:pos + 20]
        pos += 1
        skip_ws()
        first = None
        cur = None
        while text[pos] == ';':
            n = parse_node()
            if first is None:
                first = n
            else:
                cur.children.append(n)
            cur = n
            skip_ws()
        while text[pos] == '(':
            sub = parse_tree()
            cur.children.append(sub)
            skip_ws()
        assert text[pos] == ')', text[pos:pos + 20]
        pos += 1
        return first

    root = parse_tree()
    skip_ws()
    assert pos == len(text), 'trailing data'
    return root


def write_sgf(root):
    def esc(v):
        return v.replace('\\', '\\\\').replace(']', '\\]')

    def node_str(n):
        s = ';'
        for k, vs in n.props.items():
            s += k + ''.join('[%s]' % esc(v) for v in vs)
        return s

    def tree_str(n):
        s = node_str(n)
        while len(n.children) == 1:
            n = n.children[0]
            s += node_str(n)
        if n.children:
            s += ''.join('(' + tree_str(c) + ')' for c in n.children)
        return s

    return '(' + tree_str(root) + ')'


# ---------------------------------------------------------------- solver bridge
_lib = ctypes.CDLL(os.path.join(HERE, os.environ.get('SOLVERLIB', 'libsolver5.dylib')))
_lib.setup.argtypes = [ctypes.c_char_p] * 4 + [ctypes.c_int] * 5
_lib.setup.restype = ctypes.c_int
_lib.solve_all.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_longlong), ctypes.c_int]
_lib.solve_all.restype = ctypes.c_int
_lib.set_limits.argtypes = [ctypes.c_longlong, ctypes.c_int]
_lib.clear_tt.argtypes = []


class Problem:
    """A local problem: board, region, safe stones, target stones, attacker color."""

    def __init__(self, board, region, safe, target, attacker):
        self.board = board
        self.region = set(region)
        self.safe = set(safe)
        self.target = set(target)
        self.attacker = attacker

    def _strs(self, board):
        bs = ''.join({EMPTY: '.', BLACK: 'X', WHITE: 'O'}[c] for c in board.b)
        rs = ''.join('1' if i in self.region else '0' for i in range(N * N))
        ss = ''.join('1' if i in self.safe else '0' for i in range(N * N))
        ts = ''.join('1' if (i in self.target and board.b[i] == opp(self.attacker)) else '0' for i in range(N * N))
        return bs, rs, ss, ts

    def solve(self, board, tomove, kowin, strict, lastpass=0, allmoves=True, maxnodes=0, maxdepth=120):
        bs, rs, ss, ts = self._strs(board)
        ko = board.ko if board.ko is not None else -1
        if os.environ.get('CLEARTT') == '1':
            _lib.clear_tt()
        _lib.set_limits(maxnodes, maxdepth)
        _lib.setup(bs.encode(), rs.encode(), ss.encode(), ts.encode(), self.attacker, kowin, strict, ko, lastpass)
        res = (ctypes.c_int * 362)()
        stats = (ctypes.c_longlong * 2)()
        r = _lib.solve_all(tomove, res, stats, 1 if allmoves else 0)
        moves = {}
        for i in range(362):
            if res[i] >= 0:
                moves['pass' if i == 361 else i2sgf(i)] = res[i]
        return r, moves, (stats[0], stats[1])


SECONDARY_MAXNODES = 4_000_000
FAST = os.environ.get('FAST') == '1'


def classify(prob, board, tomove, solver_color, objective, maxnodes=0):
    """For side to move, classify every move. objective: 'kill' or 'live' (for solver_color).
    Returns dict move -> label among: 'win' (unconditional best), 'ko', 'seki' (life problems), 'lose'.
    Also returns overall label."""
    att = prob.attacker
    dfn = opp(att)
    out = {}
    runs = {}
    # For kill (solver=attacker): win = capture with defender winning kos; ko = capture only if attacker wins kos.
    # For live (solver=defender): win = strict life with attacker winning kos; seki = nonstrict life w/ att kos;
    # ko = strict or nonstrict life only if defender wins kos.
    if objective == 'kill':
        assert solver_color == att
        configs = [('A', dfn, 0), ('B', att, 0)]
    elif objective == 'seki':
        assert solver_color == dfn
        configs = [('A', att, 0), ('B', dfn, 0)]
    else:
        assert solver_color == dfn
        configs = [('A', att, 1), ('S', att, 0), ('B', dfn, 0)]
    if FAST:
        configs = configs[:1]
    for name, kowin, strict in configs:
        mn = maxnodes if name == 'A' else (min(maxnodes, SECONDARY_MAXNODES) if maxnodes else SECONDARY_MAXNODES)
        r, mv, st = prob.solve(board, tomove, kowin, strict, maxnodes=mn)
        runs[name] = (r, mv, st)
    moves = set()
    for name in runs:
        moves |= set(runs[name][1].keys())

    def solver_wins(name, m):
        if name not in runs:
            return None
        r, mv, st = runs[name]
        if r in (2, 3):  # already alive
            return dfn == solver_color
        if r == 4:  # targets already captured
            return att == solver_color
        w = mv.get(m)
        if w is None:
            return None
        return (w == 1) == (tomove == solver_color)

    for m in sorted(moves):
        if objective in ('kill', 'seki'):
            a = solver_wins('A', m)
            b = solver_wins('B', m)
            if a is None and runs['A'][0] == -2:
                continue
            if 'B' not in runs:
                out[m] = 'win' if a else 'lose'
                continue
            out[m] = 'win' if a else ('ko' if b else ('lose?' if b is None and runs['B'][0] == -2 else 'lose'))
        else:
            a = solver_wins('A', m)
            s = solver_wins('S', m)
            b = solver_wins('B', m)
            if a is None and runs['A'][0] == -2:
                continue
            if 'S' not in runs:
                out[m] = 'win' if a else 'lose'
                continue
            if a:
                out[m] = 'win'
            elif s:
                out[m] = 'seki'
            elif s is None and runs['S'][0] == -2:
                out[m] = 'lose?'
            elif b:
                out[m] = 'ko'
            elif b is None and runs['B'][0] == -2:
                out[m] = 'lose?'
            else:
                out[m] = 'lose'
    stats = {k: v[2] for k, v in runs.items()}
    overall = {k: v[0] for k, v in runs.items()}
    return out, overall, stats


def status(prob, board, tomove, solver_color, objective, lastpass=0):
    """Overall status with side to move: returns label for solver ('win','ko','seki','lose')."""
    att = prob.attacker
    dfn = opp(att)

    def sw(kowin, strict):
        r, mv, st = prob.solve(board, tomove, kowin, strict, lastpass=lastpass, allmoves=False)
        if r in (2, 3):
            return dfn == solver_color
        if r == 4:
            return att == solver_color
        return (r == 1) == (tomove == solver_color)

    if objective == 'kill':
        if sw(dfn, 0):
            return 'win'
        if FAST:
            return 'lose'
        if sw(att, 0):
            return 'ko'
        return 'lose'
    elif objective == 'seki':
        if sw(att, 0):
            return 'win'
        if FAST:
            return 'lose'
        if sw(dfn, 0):
            return 'ko'
        return 'lose'
    else:
        if sw(att, 1):
            return 'win'
        if FAST:
            return 'lose'
        if sw(att, 0):
            return 'seki'
        if sw(dfn, 0):
            return 'ko'
        return 'lose'


def board_from_sgf_root(root):
    b = Board()
    for v in root.props.get('AB', []):
        b.b[sgf2i(v)] = BLACK
    for v in root.props.get('AW', []):
        b.b[sgf2i(v)] = WHITE
    return b


def diagram(lines, x0=0, y0=0):
    """Parse ASCII rows. Chars: X/O stones in play, B/W safe walls (black/white), '.' empty in region,
    '-' empty outside region, 'x'/'o' stones in play and also target (defender) stones.
    Returns board, region, safe, target."""
    b = Board()
    region, safe, target = set(), set(), set()
    for dy, row in enumerate(lines):
        row = row.replace(' ', '')
        for dx, ch in enumerate(row):
            i = xy2i(x0 + dx, y0 + dy)
            if ch in 'Xx':
                b.b[i] = BLACK
                region.add(i)
            elif ch in 'Oo':
                b.b[i] = WHITE
                region.add(i)
            elif ch == 'B':
                b.b[i] = BLACK
                safe.add(i)
            elif ch == 'W':
                b.b[i] = WHITE
                safe.add(i)
            elif ch == '.':
                region.add(i)
            elif ch == '-':
                pass
            else:
                raise ValueError(ch)
            if ch in 'xo':
                target.add(i)
    return b, region, safe, target


def transform_i(i, t):
    """Apply symmetry t (0..7) to point index."""
    x, y = i % N, i // N
    if t & 1:
        x = N - 1 - x
    if t & 2:
        y = N - 1 - y
    if t & 4:
        x, y = y, x
    return y * N + x
