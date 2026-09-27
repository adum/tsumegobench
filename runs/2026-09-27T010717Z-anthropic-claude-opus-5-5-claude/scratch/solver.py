"""Local life-and-death solver.

A problem: board, region (points where moves are allowed), solver color,
goal ('live' or 'kill'), key stones (defender stones; if ANY is captured the
defender loses).  Result is True if the solver achieves the goal
unconditionally, i.e. without winning any ko: the solver's opponent may retake
kos immediately, and any repetition of a position counts as a solver loss.

Defender wins when all key stones are Benson pass-alive, or when the game ends
with two consecutive passes while key stones survive (seki counts as a defender
win unless strict=True, where only Benson life counts).
"""
from go import *

class Unknown(Exception): pass

class Solver:
    def __init__(self, board, region, solver, goal, key, strict=False, maxdepth=40, prune_eye=True):
        self.root = board
        self.region = sorted(set(region))
        self.solver = solver
        self.goal = goal
        self.defender = solver if goal == 'live' else opp(solver)
        self.attacker = opp(self.defender)
        self.key = list(key)
        self.strict = strict
        self.maxdepth = maxdepth
        self.prune_eye = prune_eye
        self.tt = {}
        self.nodes = 0
        self.depth_hit = False
        self.benson_cache = {}

    # ---- terminal tests ----
    def key_captured(self, bd):
        d = self.defender
        return any(bd.b[k] != d for k in self.key)

    def key_alive(self, bd):
        h = bd.h
        r = self.benson_cache.get(h)
        if r is None:
            alive = benson_alive(bd, self.defender)
            r = all(k in alive for k in self.key)
            self.benson_cache[h] = r
        return r

    def defender_wins_value(self):
        # value from solver's perspective
        return self.goal == 'live'

    def moves(self, bd, color):
        b = self.b = bd.b
        res = []
        for p in self.region:
            if b[p] != EMPTY: continue
            if self.prune_eye:
                own = True
                for q in NEI[p]:
                    if b[q] != color: own = False; break
                if own:
                    ok = True
                    for q in NEI[p]:
                        st, lb = bd.chain(q)
                        if len(lb) < 2: ok = False; break
                    if ok: continue
            res.append(p)
        return res

    def order(self, bd, mvs, color):
        # prioritise moves near key chain liberties and low-liberty chains
        b = bd.b
        score = {}
        keylibs = set()
        for k in self.key:
            if b[k] == self.defender:
                st, lb = bd.chain(k); keylibs |= lb
        for p in mvs:
            s = 0
            if p in keylibs: s += 3
            for q in NEI[p]:
                if b[q] != EMPTY:
                    st, lb = bd.chain(q)
                    if len(lb) <= 2: s += 3 - len(lb)
                    s += 1
            score[p] = s
        mvs.sort(key=lambda p: -score[p])
        return mvs

    def search(self, bd, color, ko, lastpass, path, depth):
        """Return (solver_wins, path_dependent)."""
        self.nodes += 1
        if self.key_captured(bd):
            return self.goal == 'kill', False
        if self.key_alive(bd):
            return self.goal == 'live', False
        if depth >= self.maxdepth:
            self.depth_hit = True
            return (self.goal == 'live'), True   # unknown: treat as defender holds, mark dependent
        tkey = (bd.h, color, ko, lastpass)
        t = self.tt.get(tkey)
        if t is not None:
            return t, False
        solver_turn = (color == self.solver)
        mvs = self.moves(bd, color)
        self.order(bd, mvs, color)
        cands = mvs + ['pass']
        dep = False
        best = not solver_turn   # default if all moves fail
        for m in cands:
            if m == 'pass':
                if lastpass:
                    # game over, key stones survive
                    val = (self.goal == 'live') if not self.strict else (self.goal == 'kill')
                    r, d = val, False
                else:
                    nk = (bd.h, opp(color))
                    if nk in path:
                        r, d = (not True), True
                        r = False
                    else:
                        path.add(nk)
                        r, d = self.search(bd, opp(color), None, True, path, depth + 1)
                        path.discard(nk)
            else:
                if m == ko and solver_turn:
                    continue
                nb = bd.copy()
                cap = nb.play(m, color)
                if cap is None: continue
                nko = None
                if len(cap) == 1:
                    st, lb = nb.chain(m)
                    if len(st) == 1 and len(lb) == 1:
                        nko = cap[0]
                nk = (nb.h, opp(color))
                if nk in path:
                    r, d = False, True
                else:
                    path.add(nk)
                    r, d = self.search(nb, opp(color), nko, False, path, depth + 1)
                    path.discard(nk)
            dep = dep or d
            if solver_turn and r:
                best = True; break
            if not solver_turn and not r:
                best = False; break
        if not dep:
            self.tt[tkey] = best
        return best, dep

    def solve(self, bd, color, ko=None, lastpass=False):
        path = {(bd.h, color)}
        r, d = self.search(bd, color, ko, lastpass, path, 0)
        return r

    def winning_moves(self, bd, color, ko=None):
        """For each legal move of `color` (plus pass), whether solver wins after it."""
        out = {}
        for m in self.moves(bd, color) + ['pass']:
            if m == 'pass':
                path = {(bd.h, color), (bd.h, opp(color))}
                r, d = self.search(bd, opp(color), None, True, path, 1)
                out['pass'] = r
                continue
            if m == ko and color == self.solver: continue
            nb = bd.copy(); cap = nb.play(m, color)
            if cap is None: continue
            nko = None
            if len(cap) == 1:
                st, lb = nb.chain(m)
                if len(st) == 1 and len(lb) == 1: nko = cap[0]
            path = {(bd.h, color), (nb.h, opp(color))}
            r, d = self.search(nb, opp(color), nko, False, path, 1)
            out[i2s(m)] = r
        return out
