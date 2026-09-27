"""Automatic solution-tree builder guided by the solver."""
from tl import *

class Auto:
    def __init__(self, spec, K=3, maxply=13):
        self.spec = spec; self.K = K; self.maxply = maxply
        self.cache = {}
    def an(self, bd, c, ko):
        key = (bd.h, c, ko)
        if key not in self.cache:
            self.cache[key] = run(self.spec, bd, c, ko)
        return self.cache[key]
    def wins(self, bd, c, ko):
        a = self.an(bd, c, ko)
        return sorted([m for m, v in a.items() if v[0] == 'W' and m != 'pass'], key=lambda m: a[m][1])
    def settled(self, bd, c, ko, depth=0):
        """Opponent (c) to move after a solver move: return critical replies."""
        S = self.spec.solver
        a = self.an(bd, c, ko)
        crit = []
        for m, v in a.items():
            if v[0] != 'W': raise ValueError('solver not winning here')
            if m == 'pass': continue
            nb, nko = apply(bd, m, c)
            if self.terminal(nb): continue
            a2 = self.an(nb, S, nko)
            if a2.get('pass', ('L',))[0] == 'W': continue      # solver may ignore it
            w = [k for k, x in a2.items() if x[0] == 'W' and k != 'pass']
            if len(w) >= self.K: continue
            if depth < 2:
                ok = False
                for k in w:
                    if self.obvious(nb, k, S):
                        nb2, nko2 = apply(nb, k, S)
                        if self.terminal(nb2) or not self.settled(nb2, c, nko2, depth + 1):
                            ok = True; break
                if ok: continue
            crit.append((m, v[1], sorted(w, key=lambda k: a2[k][1])))
        crit.sort(key=lambda r: -r[1])
        return crit
    def obvious(self, bd, mv, col):
        """Move captures something, or saves a chain of col that is in atari."""
        i = s2i(mv)
        nb = bd.copy(); cap = nb.play(i, col)
        if cap: return True
        for q in NEI[i]:
            if bd.b[q] == col:
                st, lb = bd.chain(q)
                if len(lb) == 1: return True
        return False
    def terminal(self, bd):
        sp = self.spec
        d = sp.solver if sp.goal == 'live' else opp(sp.solver)
        return any(bd.b[k] != d for k in sp.key)
    def build_right(self, bd, c, ko, ply, line):
        """Solver to move at bd; returns list of (move, subtree) for all winning moves."""
        S = self.spec.solver
        out = []
        for m in self.wins(bd, c, ko):
            nb, nko = apply(bd, m, c)
            sub = self.build_opp(nb, opp(c), nko, ply + 1, line + [m])
            out.append((m, sub))
        return out
    def build_opp(self, bd, c, ko, ply, line):
        if self.terminal(bd): return 'RIGHT'
        crit = self.settled(bd, c, ko)
        if not crit: return 'RIGHT'
        if ply >= self.maxply:
            return 'TOO_DEEP'
        out = []
        for m, d, w in crit:
            nb, nko = apply(bd, m, c)
            out.append((m, self.build_right(nb, opp(c), nko, ply + 1, line + [m])))
        return out

def show_tree(t, indent=0, col='B'):
    pad = '  ' * indent
    if isinstance(t, str): print(pad + t); return
    for m, sub in t:
        if isinstance(sub, str): print(pad + f'{col}[{m}] {sub}')
        else:
            print(pad + f'{col}[{m}]')
            show_tree(sub, indent + 1, 'W' if col == 'B' else 'B')

def count(t):
    if isinstance(t, str): return 0
    return sum(1 + count(s) for m, s in t)

def to_sgf_tree(t, col):
    """Convert to SGF variation text."""
    if isinstance(t, str): return ''
    other = 'W' if col == 'B' else 'B'
    parts = []
    for m, sub in t:
        s = f';{col}[{m}]'
        if sub == 'RIGHT': s += 'C[RIGHT]'
        elif isinstance(sub, list):
            inner = to_sgf_tree(sub, other)
            s += inner
        parts.append(s)
    if len(parts) == 1: return parts[0]
    return ''.join('(' + p + ')' for p in parts)

def opp_spec(spec):
    s = spec.with_(solver='B' if spec.solver == WHITE else 'W')
    s.goal = 'kill' if spec.goal == 'live' else 'live'
    return s

class AutoWrong:
    """Build refutation lines. Opponent spec: opponent as 'solver' with reversed goal."""
    def __init__(self, spec):
        self.spec = spec
        self.ospec = opp_spec(spec)
        self.cache = {}
    def an(self, sp, bd, c, ko):
        key = (id(sp), bd.h, c, ko)
        if key not in self.cache: self.cache[key] = run(sp, bd, c, ko)
        return self.cache[key]
    def refutations(self, bd, c, ko):
        """Opponent (c) to move after a wrong solver move. Return list of (move, kind, depth)
        kind 'clean' if opponent wins unconditionally, 'ko' if solver merely fails to win."""
        a1 = self.an(self.spec, bd, c, ko)       # solver's perspective
        a2 = self.an(self.ospec, bd, c, ko)      # opponent's perspective
        out = []
        for m, v in a1.items():
            if v[0] != 'W':
                kind = 'clean' if a2.get(m, ('?',))[0] == 'W' else 'ko/unclear'
                out.append((m, kind, a2.get(m, ('?', 0))[1]))
        out.sort(key=lambda r: (r[1] != 'clean', r[2]))
        return out
    def answers(self, bd, c, ko):
        """Solver (c) to move after refutation: for each solver try, opponent's clean answers."""
        a = self.an(self.ospec, bd, c, ko)  # c is ospec's opponent here
        res = []
        for m, v in a.items():
            if m == 'pass': continue
            if v[0] == 'W':
                nb, nko = apply(bd, m, c)
                a2 = self.an(self.ospec, nb, opp(c), nko)
                ans = sorted(k for k, w in a2.items() if w[0] == 'W' and k != 'pass')
                res.append((m, len(ans), ans))
            else:
                res.append((m, 'SOLVER-OK?', []))
        res.sort(key=lambda r: r[1] if isinstance(r[1], int) else -1)
        return res
