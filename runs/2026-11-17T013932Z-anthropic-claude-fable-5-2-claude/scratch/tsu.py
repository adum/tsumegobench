"""Helpers for authoring/verifying local life-and-death problems.

Diagram characters (top-left corner of the board is diagram row 0, col 0):
  X / O : black / white wall stone (outside region)
  x / o : black / white stone inside the region (point playable if captured)
  @     : defender target stone (inside region); attacker wins if any captured
  +     : empty region point (both may play)
  a     : empty point only the attacker may play (outside liberty)
  .     : empty, not playable
"""
import subprocess, os, sys, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVER = os.path.join(HERE, 'solver')


def pt(x, y):
    return chr(97 + x) + chr(97 + y)


def xy(s):
    return ord(s[0]) - 97, ord(s[1]) - 97


class Problem:
    def __init__(self, diagram, defender, first, maxnodes=3000000):
        self.defender = defender
        self.attacker = 'B' if defender == 'W' else 'W'
        self.first = first  # solver colour
        self.black, self.white = [], []
        self.regboth, self.regatt, self.target = [], [], []
        rows = [r for r in diagram.strip('\n').split('\n')]
        self.rows = rows
        for y, row in enumerate(rows):
            row = row.replace(' ', '')
            for x, ch in enumerate(row):
                p = pt(x, y)
                if ch == 'X':
                    self.black.append(p)
                elif ch == 'O':
                    self.white.append(p)
                elif ch == 'x':
                    self.black.append(p); self.regboth.append(p)
                elif ch == 'o':
                    self.white.append(p); self.regboth.append(p)
                elif ch == '@':
                    (self.black if defender == 'B' else self.white).append(p)
                    self.regboth.append(p); self.target.append(p)
                elif ch == '+':
                    self.regboth.append(p)
                elif ch == 'a':
                    self.regatt.append(p)
                elif ch == '.':
                    pass
                else:
                    raise ValueError('bad char %r' % ch)
        self.maxnodes = maxnodes
        self.seeds = [(None if x == 'n' else x) for x in os.environ.get('ROBUST', '').split(',') if x] or [None]
        self.procs = {}
        self.cache = {}
        self.disagree = []

    def start(self, seed=None):
        env = dict(os.environ)
        env.pop('TSEED', None)
        if seed is not None:
            env['TSEED'] = str(seed)
        elif os.environ.get('TSEED'):
            env['TSEED'] = os.environ['TSEED']
        proc = subprocess.Popen([SOLVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        w = proc.stdin.write
        w('attacker %s\n' % self.attacker)
        w('black %s\n' % ' '.join(self.black))
        w('white %s\n' % ' '.join(self.white))
        w('regboth %s\n' % ' '.join(self.regboth))
        w('regatt %s\n' % ' '.join(self.regatt))
        w('target %s\n' % ' '.join(self.target))
        w('ready\n')
        proc.stdin.flush()
        assert proc.stdout.readline().strip() == 'OK'
        self.procs[seed] = proc

    def close(self):
        for proc in self.procs.values():
            proc.stdin.close()
            proc.wait()
        self.procs = {}

    def colour_at(self, n):
        """colour of the n-th move (0-based) in a line"""
        other = 'B' if self.first == 'W' else 'W'
        return self.first if n % 2 == 0 else other

    def _raw(self, kw, moves, seed=None):
        if seed not in self.procs:
            self.start(seed)
        proc = self.procs[seed]
        toks = []
        for i, m in enumerate(moves):
            toks.append(self.colour_at(i)); toks.append(m)
        tomove = self.colour_at(len(moves))
        proc.stdin.write('q %s %d %s %s\n' % (kw, self.maxnodes, tomove, ' '.join(toks)))
        proc.stdin.flush()
        res = {}
        status = None
        while True:
            line = proc.stdout.readline().strip()
            if line == 'END':
                break
            if line.startswith('ERR'):
                status = line
                continue
            if line == 'CAPTURED':
                status = 'CAPTURED'
                continue
            m, r = line.split()
            res[m] = r
        return status, res

    def _query1(self, moves, seed):
        sD, rD = self._raw('D', moves, seed)
        sA, rA = self._raw('A', moves, seed)
        if sD or sA:
            return (sD or sA, {})
        vals = {}
        tomove = self.colour_at(len(moves))
        kopt = self.ko_point(moves)
        worst = '0' if tomove == self.attacker else '1'   # banned ko capture = worst result for the mover
        for m in sorted(set(rD) | set(rA)):
            d, a = rD.get(m, 'ko'), rA.get(m, 'ko')
            if d == 'ko':
                d = worst
            if a == 'ko':
                a = worst
            if m == kopt:
                continue   # immediate ko recapture is illegal
            vals[m] = self._val(d, a)
        return (None, vals)

    def query(self, moves):
        """Return (status, {move: value}) where value is from the SOLVER's perspective
        of the position after that move: 2 = solver succeeds outright, 1 = ko, 0 = fails,
        -1 = unknown (node limit or disagreement between search orders).
        status: None, 'CAPTURED' or 'ERR ...'"""
        key = tuple(moves)
        if key in self.cache:
            return self.cache[key]
        outs = [self._query1(moves, sd) for sd in self.seeds]
        st, vals = outs[0]
        vals = dict(vals)
        for o in outs[1:]:
            if o[0] != st:
                self.disagree.append((key, 'status', [x[0] for x in outs]))
            for m in vals:
                if o[1].get(m) != vals[m] and vals[m] != -1:
                    self.disagree.append((key, m, [x[1].get(m) for x in outs]))
                    vals[m] = -1
        out = (st, vals)
        self.cache[key] = out
        return out

    def _val(self, d, a, kolimited=False):
        if d == '?' or a == '?':
            return -1
        # d: attacker wins when defender is ko-winner; a: attacker wins when attacker is ko-winner
        if self.first == self.attacker:
            if d == '1':
                return 2
            if a == '1':
                return 1
            return 0
        else:
            if a == '0':
                return 2
            if d == '0':
                return 1
            return 0

    def ko_point(self, moves):
        """point banned by the simple ko rule after replaying moves (or None)"""
        g = {}
        for q in self.black:
            g[q] = 'X'
        for q in self.white:
            g[q] = 'O'
        ko = None
        for i, m in enumerate(moves):
            ko = None
            if m == 'pass':
                continue
            caps = play(g, m, 'X' if self.colour_at(i) == 'B' else 'O')
            if len(caps) == 1:
                grp, libs = group(g, m)
                if len(grp) == 1 and len(libs) == 1:
                    ko = caps[0]
        return ko

    # ---------- display -----------
    def board(self, moves=()):
        """ASCII board after moves (simple replay with captures)."""
        g = {}
        for p in self.black:
            g[p] = 'X'
        for p in self.white:
            g[p] = 'O'
        for i, m in enumerate(moves):
            if m == 'pass':
                continue
            play(g, m, 'X' if self.colour_at(i) == 'B' else 'O')
        return g

    def show(self, moves=(), w=None, hgt=None):
        g = self.board(moves)
        hgt = hgt or len(self.rows) + 1
        w = w or max(len(r.replace(' ', '')) for r in self.rows) + 1
        out = ['   ' + ' '.join(chr(97 + x) for x in range(w))]
        for y in range(hgt):
            out.append(' %s ' % chr(97 + y) + ' '.join(g.get(pt(x, y), '.') for x in range(w)))
        return '\n'.join(out)

    def report(self, moves=()):
        st, vals = self.query(list(moves))
        if st:
            return st
        s = []
        for m, v in sorted(vals.items(), key=lambda kv: (-kv[1], kv[0])):
            s.append('%s:%s' % (m, {2: 'WIN', 1: 'ko', 0: 'x', -1: '?'}[v]))
        return ' '.join(s)


def neighbours(p):
    x, y = xy(p)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < 19 and 0 <= ny < 19:
            yield pt(nx, ny)


def group(g, p):
    col = g[p]
    seen = {p}
    st = [p]
    libs = set()
    while st:
        q = st.pop()
        for n in neighbours(q):
            if n not in g:
                libs.add(n)
            elif g[n] == col and n not in seen:
                seen.add(n); st.append(n)
    return seen, libs


def play(g, p, col):
    """play on dict board; returns list of captured points; raises on illegal"""
    if p in g:
        raise ValueError('occupied ' + p)
    g[p] = col
    caps = []
    for n in neighbours(p):
        if n in g and g[n] != col:
            grp, libs = group(g, n)
            if not libs:
                for q in grp:
                    del g[q]
                    caps.append(q)
    grp, libs = group(g, p)
    if not libs:
        del g[p]
        raise ValueError('suicide ' + p)
    return caps


# ---------------- tree building -----------------

class Node:
    def __init__(self, move=None):
        self.move = move
        self.children = []
        self.right = False
        self.comment = None

    def add(self, child):
        self.children.append(child)
        return child


def count_nodes(n):
    return (1 if n.move else 0) + sum(count_nodes(c) for c in n.children)


def max_depth(n):
    d = 1 if n.move else 0
    return d + max([max_depth(c) for c in n.children] or [0])


def to_sgf(prob, root, transform=None):
    tf = transform or (lambda p: p)
    def mv(n, depth):
        col = prob.colour_at(depth)
        s = ';%s[%s]' % (col, tf(n.move))
        if n.right:
            s += 'C[RIGHT]'
        elif n.comment:
            s += 'C[%s]' % n.comment
        if len(n.children) == 1:
            s += mv(n.children[0], depth + 1)
        else:
            for c in n.children:
                s += '(' + mv(c, depth + 1) + ')'
        return s
    ab = ''.join('[%s]' % tf(p) for p in sorted(tf(q) and q for q in prob.black))
    aw = ''.join('[%s]' % tf(p) for p in sorted(prob.white))
    ab = ''.join('[%s]' % p for p in sorted(tf(q) for q in prob.black))
    aw = ''.join('[%s]' % p for p in sorted(tf(q) for q in prob.white))
    body = ''
    if len(root.children) == 1:
        body = '(' + mv(root.children[0], 0) + ')'
    else:
        body = ''.join('(' + mv(c, 0) + ')' for c in root.children)
    return '(;FF[4]GM[1]SZ[19]AB%sAW%s%s)\n' % (ab, aw, body)


TRANSFORMS = {
    'id': lambda x, y: (x, y),
    'flipx': lambda x, y: (18 - x, y),          # top-right
    'flipy': lambda x, y: (x, 18 - y),          # bottom-left
    'rot180': lambda x, y: (18 - x, 18 - y),    # bottom-right
    'transpose': lambda x, y: (y, x),           # top-left mirrored
    'tr_flipx': lambda x, y: (18 - y, x),       # top-right (transposed)
    'tr_flipy': lambda x, y: (y, 18 - x),       # bottom-left (transposed)
    'tr_rot180': lambda x, y: (18 - y, 18 - x), # bottom-right (transposed)
}


def make_tf(name, shift=(0, 0)):
    f = TRANSFORMS[name]
    def tf(p):
        x, y = xy(p)
        x, y = x + shift[0], y + shift[1]
        x, y = f(x, y)
        assert 0 <= x < 19 and 0 <= y < 19
        return pt(x, y)
    return tf


class Builder:
    """Automatic draft tree builder.

    best: value treated as success (2 normally).
    """
    def __init__(self, prob, best=2, max_wrong_root=8, max_wrong_inner=3, followups=2,
                 max_threats=4, include=None, exclude=None, refute_with=None, stop_at=None,
                 extra_followups=None, no_wrong_at=None, max_len=13, force_reply=None):
        self.p = prob
        self.best = best
        self.max_wrong_root = max_wrong_root
        self.max_wrong_inner = max_wrong_inner
        self.followups = followups
        self.max_threats = max_threats
        self.include = include or {}       # path-tuple -> list of wrong moves to include (overrides auto)
        self.exclude = exclude or {}       # path-tuple -> moves to skip
        self.refute_with = refute_with or {}  # path-tuple(after wrong move) -> refuting reply
        self.stop_at = stop_at or set()    # path tuples (ending on solver move) forced to be RIGHT leaves
        self.extra_followups = extra_followups or {}
        self.no_wrong_at = no_wrong_at or set()
        self.force_reply = force_reply or {}  # path (ending on solver right move) -> list of replies
        self.max_len = max_len
        self.log = []

    def vals(self, moves):
        st, v = self.p.query(list(moves))
        return st, {m: x for m, x in v.items()}

    def is_threat(self, moves):
        """moves ends with an opponent move. True if solver cannot ignore it (pass does not keep success)."""
        st, v = self.vals(moves)
        if st:
            return True
        return v.get('pass', 0) < self.best

    def solver_node(self, node, moves, on_root=False):
        st, v = self.vals(moves)
        assert not st, (st, moves)
        wins = [m for m, x in v.items() if x >= self.best and m != 'pass']
        assert wins, ('no winning move', moves)
        for m in sorted(wins):
            c = node.add(Node(m))
            self.opp_node(c, moves + (m,))
        key = tuple(moves)
        if key in self.no_wrong_at:
            return
        if key in self.include:
            wrong = list(self.include[key])
        else:
            wrong = [m for m, x in v.items() if x < self.best and m != 'pass' and m not in self.exclude.get(key, ())]
            cap = self.max_wrong_root if on_root else self.max_wrong_inner
            # prefer moves that are threats-ish: order by value desc (ko first) then name
            wrong.sort(key=lambda m: (-v[m], m))
            wrong = wrong[:cap]
        for m in wrong:
            if m in wins:
                raise ValueError('include lists winning move %s at %s' % (m, key))
            c = node.add(Node(m))
            self.refute(c, moves + (m,), self.followups if on_root else max(0, self.followups - 1))

    def opp_node(self, node, moves):
        """node = solver's winning move just played."""
        key = tuple(moves)
        st, v = self.vals(moves)
        if st == 'CAPTURED' or key in self.stop_at or len(moves) >= self.max_len:
            node.right = True
            return
        assert not st, (st, moves)
        if key in self.force_reply:
            threats = [(0, r) for r in self.force_reply[key]]
        else:
            threats = []
            for r in v:
                if r == 'pass' or r in self.exclude.get(key, ()):
                    continue
                mm = moves + (r,)
                st2, v2 = self.vals(mm)
                if st2:
                    continue
                if v2.get('pass', 0) >= self.best:
                    continue
                nwin = sum(1 for m, x in v2.items() if x >= self.best and m != 'pass')
                threats.append((nwin, r))
            threats.sort()
            threats = threats[:self.max_threats]
        if not threats:
            node.right = True
            return
        for nwin, r in threats:
            c = node.add(Node(r))
            self.solver_node(c, moves + (r,))

    def refute(self, node, moves, followups):
        """node = solver's wrong move just played; add opponent's refutation."""
        key = tuple(moves)
        st, v = self.vals(moves)
        assert not st, (st, moves)
        cands = {r: x for r, x in v.items()}
        lo = min(cands.values())
        assert lo < self.best, ('not refutable', moves, cands)
        if key in self.refute_with:
            r = self.refute_with[key]
            assert cands.get(r, 9) < self.best, ('given refutation fails', moves, r, cands)
        else:
            best = None
            for r, x in sorted(cands.items()):
                if x != lo:
                    continue
                if r == 'pass':
                    continue
                # count solver continuations that still need an answer
                st2, v2 = self.vals(moves + (r,))
                if st2:
                    continue
                nthr = 0
                for m in v2:
                    if m == 'pass':
                        continue
                    st3, v3 = self.vals(moves + (r, m))
                    if st3 == 'CAPTURED':
                        nthr += 100
                        continue
                    if st3:
                        continue
                    # opponent passes: does solver then succeed?
                    if v3.get('pass', 0) >= self.best:
                        nthr += 1
                if best is None or nthr < best[0]:
                    best = (nthr, r)
            if best is None:
                # only pass refutes -> the wrong move needs no answer; leave bare
                node.comment = None
                self.log.append(('pass-refutes', moves))
                return
            r = best[1]
        c = node.add(Node(r))
        if lo == 1:
            c.comment = 'ko'
        mm = moves + (r,)
        fl = self.extra_followups.get(tuple(mm))
        if fl is None and followups > 0:
            st2, v2 = self.vals(mm)
            fl = []
            for m in sorted(v2):
                if m == 'pass':
                    continue
                st3, v3 = self.vals(mm + (m,))
                if st3 or v3.get('pass', 0) >= self.best:
                    fl.append(m)
            fl = fl[:self.max_wrong_inner]
        for m in (fl or []):
            cc = c.add(Node(m))
            self.refute(cc, mm + (m,), followups - 1 if followups else 0)

    def build(self):
        root = Node()
        self.solver_node(root, (), on_root=True)
        return root


def dump(prob, node, moves=(), indent=0, out=None):
    out = out if out is not None else []
    for c in node.children:
        tag = ' RIGHT' if c.right else (' [%s]' % c.comment if c.comment else '')
        out.append('  ' * indent + '%s %s%s' % (prob.colour_at(len(moves)), c.move, tag))
        dump(prob, c, moves + (c.move,), indent + 1, out)
    return out
