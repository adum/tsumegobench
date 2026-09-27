"""Structural + solver-based validation of a problem SGF."""
from gotools import *

MAXLINE = 14
MAXNODES = 120


class Spec:
    def __init__(self, region, safe, target, attacker, objective, solver):
        self.region = set(region)
        self.safe = set(safe)
        self.target = set(target)
        self.attacker = attacker
        self.objective = objective  # 'kill' or 'live' (for solver)
        self.solver = solver


def structural(root):
    errs = []
    p = root.props
    if p.get('SZ') != ['19']:
        errs.append('SZ[19] missing')
    if not p.get('AB') or not p.get('AW'):
        errs.append('AB/AW missing')
    if 'B' in p or 'W' in p:
        errs.append('move at root')
    if 'C' in p:
        errs.append('comment at root')
    firsts = set()
    for c in root.children:
        mv = c.move()
        if mv:
            firsts.add(mv[0])
    if len(firsts) != 1:
        errs.append('inconsistent first color %s' % firsts)
    count = [1]
    maxlen = [0]
    b0 = board_from_sgf_root(root)
    if len(set(p.get('AB', [])) & set(p.get('AW', []))):
        errs.append('overlapping setup')
    # check setup legality: no group without liberties
    for i in range(361):
        if b0.b[i]:
            st, lb = b0.chain(i)
            if not lb:
                errs.append('setup chain without liberties at %s' % i2sgf(i))
                break

    def rec(node, board, color, depth, pathstr):
        for ch in node.children:
            count[0] += 1
            keys = [k for k in ('B', 'W') if k in ch.props]
            if len(keys) != 1:
                errs.append('node without exactly one move at %s' % pathstr)
                continue
            k = keys[0]
            c = BLACK if k == 'B' else WHITE
            if c != color:
                errs.append('color alternation broken at %s' % pathstr)
            v = ch.props[k][0]
            if len(v) != 2 or v == 'tt':
                errs.append('pass/invalid move at %s' % pathstr)
                continue
            nb = board.copy()
            try:
                nb.play(sgf2i(v), c)
            except IllegalMove as e:
                errs.append('illegal %s at %s: %s' % (v, pathstr, e))
                continue
            cm = ch.comment()
            if 'RIGHT' in cm and ch.children:
                errs.append('RIGHT on non-leaf at %s %s' % (pathstr, v))
            if '<' in cm or '>' in cm:
                errs.append('html in comment')
            if depth + 1 > maxlen[0]:
                maxlen[0] = depth + 1
            rec(ch, nb, opp(c), depth + 1, pathstr + ' ' + k + v)

    first = list(firsts)[0] if firsts else BLACK
    rec(root, b0, first, 0, '')
    if maxlen[0] > MAXLINE:
        errs.append('line too long %d' % maxlen[0])
    if count[0] > MAXNODES:
        errs.append('too many nodes %d' % count[0])
    return errs, count[0], maxlen[0]


def has_right(node):
    if 'RIGHT' in node.comment():
        return True
    return any(has_right(c) for c in node.children)


_cache = {}


def cls(prob, board, tomove, spec, maxnodes):
    key = (tuple(board.b), board.ko, tomove)
    if key not in _cache:
        res, overall, stats = classify(prob, board, tomove, spec.solver, spec.objective, maxnodes=maxnodes)
        if overall.get('A') == -2:
            print('ABORT at position (tomove=%s):' % CNAME[tomove])
            print(board.show())
            print('overall', overall, 'stats', stats, 'partial', res)
            raise RuntimeError('solver aborted (node limit) at position')
        if not res and (all(v in (2, 3) for v in overall.values()) or all(v == 4 for v in overall.values())):
            # defender already unconditionally alive (2/3) or already captured (4): label all legal moves
            if all(v == 4 for v in overall.values()):
                lab = 'win' if spec.solver == spec.attacker else 'lose'
            else:
                lab = 'win' if spec.solver != spec.attacker else 'lose'
            res = {}
            for i in prob.region:
                if board.b[i] == EMPTY:
                    nb = board.copy()
                    try:
                        nb.play(i, tomove)
                    except IllegalMove:
                        continue
                    res[i2sgf(i)] = lab
            res['pass'] = lab
        _cache[key] = (res, overall, stats)
    return _cache[key]


def semantic(root, spec, maxnodes=20_000_000, verbose=True, defense_report=True):
    """Walk tree and check solver facts. Returns list of problems found and notes."""
    errs, notes = [], []
    b0 = board_from_sgf_root(root)
    prob = Problem(b0, spec.region, spec.safe, spec.target, spec.attacker)
    S = spec.solver

    def best_label(res):
        order = ['win', 'seki', 'ko', 'lose']
        labs = [v for m, v in res.items()]
        for o in order:
            if o in labs:
                return o
        return 'lose'

    def rec(node, board, tomove, pathstr, on_right_path):
        if tomove == S:
            res, overall, stats = cls(prob, board, tomove, spec, maxnodes)
            bestl = best_label(res)
            winners = sorted(m for m, v in res.items() if v == bestl) if bestl != 'lose' else []
            if not node.children:
                # leaf with solver to move: must be failure (end of wrong line)
                if bestl == 'ko' and 'ko' in node.comment().lower():
                    notes.append('[%s] wrong line ends in ko (commented): solver ko via %s' % (pathstr, winners))
                elif bestl == 'seki' and 'seki' in node.comment().lower():
                    notes.append('[%s] wrong line ends in seki (commented)' % pathstr)
                elif bestl != 'lose':
                    errs.append('[%s] leaf with solver to move but solver still has %s via %s' % (pathstr, bestl, winners))
                return
            if bestl == 'lose' and has_right(node):
                errs.append('[%s] solver to move but no successful move exists (res=%s)' % (pathstr, res))
            if not has_right(node):
                # inside a wrong line: solver keeps trying; every solver try must still fail
                for ch in node.children:
                    mv = ch.move()
                    if res.get(mv[1]) != 'lose' and bestl == 'lose':
                        errs.append('[%s] wrong-line try %s has label %s' % (pathstr, mv[1], res.get(mv[1])))
                for ch in node.children:
                    mv = ch.move()
                    nb = board.copy()
                    nb.play(sgf2i(mv[1]), mv[0])
                    rec(ch, nb, opp(tomove), pathstr + ' ' + CNAME[mv[0]] + mv[1], False)
                return
            tree_moves = {}
            for ch in node.children:
                mv = ch.move()
                tree_moves[mv[1]] = ch
            for m in winners:
                if m == 'pass':
                    notes.append('[%s] pass is also %s' % (pathstr, bestl))
                    continue
                if m not in tree_moves:
                    errs.append('[%s] missing correct move %s (%s)' % (pathstr, m, bestl))
                elif not has_right(tree_moves[m]):
                    errs.append('[%s] correct move %s marked wrong' % (pathstr, m))
            for m, ch in tree_moves.items():
                lab = res.get(m, '??')
                if has_right(ch) and m not in winners:
                    errs.append('[%s] move %s has RIGHT but label=%s (best=%s)' % (pathstr, m, lab, bestl))
                if not has_right(ch) and verbose:
                    notes.append('[%s] wrong move %s label=%s' % (pathstr, m, lab))
            if verbose:
                notes.append('[%s] solver-to-move labels: %s' % (pathstr, ' '.join('%s:%s' % (m, v) for m, v in sorted(res.items()))))
            for ch in node.children:
                mv = ch.move()
                nb = board.copy()
                nb.play(sgf2i(mv[1]), mv[0])
                rec(ch, nb, opp(tomove), pathstr + ' ' + CNAME[mv[0]] + mv[1], on_right_path and has_right(ch))
        else:
            # opponent to move. Determine status for solver with opponent to move.
            res, overall, stats = cls(prob, board, tomove, spec, maxnodes)
            # res labels are from solver perspective already (classify uses solver_color)
            # opponent best = move giving solver worst label
            order = ['lose', 'lose?', 'ko', 'seki', 'win']
            worst = None
            for o in order:
                if any(v == o for v in res.values()):
                    worst = o
                    break
            is_right_leaf = (not node.children) and 'RIGHT' in node.comment()
            if has_right(node):
                # solver's last move was claimed correct: every opponent move must leave solver at 'win'-class
                if worst != 'win' and not (spec.objective == 'live' and worst in ('win',)):
                    errs.append('[%s] after claimed-correct move, opponent can reach %s via %s' % (
                        pathstr, worst, sorted(m for m, v in res.items() if v == worst)))
                if not node.children and not is_right_leaf:
                    errs.append('[%s] leaf on right path without RIGHT' % pathstr)
                if defense_report:
                    # threats (replies the solver cannot ignore) and their answers
                    import etree
                    etree.MAXNODES = maxnodes
                    tree_moves = {ch.move()[1] for ch in node.children}
                    import gotools as _g
                    _saved = _g.FAST
                    _g.FAST = True
                    etree._cache.clear(); etree._scache.clear()
                    try:
                        ok, th = etree.threats(prob, board, S, spec.objective)
                    finally:
                        _g.FAST = _saved
                        etree._cache.clear(); etree._scache.clear()
                    info = []
                    for om, w3, nb2, lab in th:
                        w3 = [w for w in w3 if w != 'pass']
                        info.append((om, w3))
                        if om not in tree_moves and len(w3) <= 2:
                            notes.append('[%s] UNCOVERED threat %s -> solver answers %s' % (pathstr, om, w3))
                    if verbose and info:
                        notes.append('[%s] threats: %s' % (pathstr, '; '.join('%s->%s' % (m, ','.join(n) if len(n) <= 4 else '%d moves' % len(n)) for m, n in info)))
                    for ch in node.children:
                        mv = ch.move()[1]
                        if mv not in [t[0] for t in th]:
                            notes.append('[%s] tree includes non-threat defense %s' % (pathstr, mv))
            else:
                # wrong path: the solver's last move is wrong; tree should show refutation.
                if not node.children:
                    errs.append('[%s] wrong line ends on solver move without refutation' % pathstr)
                for ch in node.children:
                    mv = ch.move()
                    lab = res.get(mv[1], '??')
                    if lab == 'lose?' and worst in ('lose', 'lose?'):
                        notes.append('[%s] refutation %s: failure confirmed, ko-vs-death undetermined' % (pathstr, mv[1]))
                    elif lab not in ('lose', 'ko', 'seki') or (lab != 'lose' and worst == 'lose'):
                        errs.append('[%s] refutation %s is not best (label %s, best refutation gives %s: %s)' % (
                            pathstr, mv[1], lab, worst, sorted(m for m, v in res.items() if v == worst)))
            for ch in node.children:
                mv = ch.move()
                nb = board.copy()
                nb.play(sgf2i(mv[1]), mv[0])
                rec(ch, nb, opp(tomove), pathstr + ' ' + CNAME[mv[0]] + mv[1], has_right(ch))

    first = root.children[0].move()[0]
    rec(root, b0, first, '', True)
    return errs, notes


def check(sgf_text, spec, maxnodes=20_000_000, verbose=True):
    root = parse_sgf(sgf_text)
    e1, count, maxlen = structural(root)
    print('structural errors:', e1, 'nodes:', count, 'maxline:', maxlen)
    e2, notes = semantic(root, spec, maxnodes=maxnodes, verbose=verbose)
    for n in notes:
        print('  note:', n)
    for e in e2:
        print('  ERROR:', e)
    return e1 + e2
