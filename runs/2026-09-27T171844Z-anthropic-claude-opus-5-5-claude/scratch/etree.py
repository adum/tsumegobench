"""Essential tree using threat test: an opponent reply is a threat if the solver would fail by ignoring it."""
import sys
from gotools import *

_cache = {}
_scache = {}
MAXNODES = 5_000_000


def labels(prob, board, tomove, solver, objective, maxnodes=None):
    if maxnodes is None:
        maxnodes = MAXNODES
    key = (tuple(board.b), board.ko, tomove, id(prob))
    if key in _cache:
        return _cache[key]
    res, overall, stats = classify(prob, board, tomove, solver, objective, maxnodes=maxnodes)
    if overall.get('A') == -2:
        raise RuntimeError('abort')
    if not res and all(v in (2, 3) for v in overall.values()):
        lab = 'win' if solver != prob.attacker else 'lose'
        res = {'*settled*': lab}
    elif not res and all(v == 4 for v in overall.values()):
        lab = 'win' if solver == prob.attacker else 'lose'
        res = {'*settled*': lab}
    _cache[key] = res
    return res


def stat(prob, board, tomove, solver, objective):
    key = (tuple(board.b), board.ko, tomove, id(prob))
    if key not in _scache:
        _scache[key] = status(prob, board, tomove, solver, objective)
    return _scache[key]


def winning(res):
    return sorted(m for m, v in res.items() if v == 'win')


def after(board, m, c):
    nb = board.copy()
    if m != 'pass':
        nb.play(sgf2i(m), c)
    else:
        nb.ko = None
    return nb


def threats(prob, board, solver, objective):
    """board: after solver's move, opponent to move. Returns (all_ok, list of (reply, solver answers)) for threat replies."""
    o = opp(solver)
    r2 = labels(prob, board, o, solver, objective)
    if '*settled*' in r2:
        return r2['*settled*'] == 'win', []
    ok = all(v == 'win' for v in r2.values())
    out = []
    for om in sorted(r2):
        if om == 'pass':
            continue
        try:
            nb2 = after(board, om, o)
        except IllegalMove:
            continue
        # threat test: solver ignores (passes) -> opponent to move again
        nb2t = nb2.copy()
        nb2t.ko = None
        st = stat(prob, nb2t, o, solver, objective)
        if st != 'win':
            r3 = labels(prob, nb2, solver, solver, objective)
            if '*settled*' in r3:
                w3 = ['(settled)']
            else:
                w3 = winning(r3)
            out.append((om, w3, nb2, r2[om]))
    return ok, out


def etree(prob, board, solver, objective, maxdepth=12, depth=0, indent='', maxwins=3):
    res = labels(prob, board, solver, solver, objective)
    if '*settled*' in res:
        print(indent + '(settled: %s)' % res['*settled*'])
        return
    wins = winning(res)
    if not wins:
        print(indent + 'SOLVER FAILS here; labels: %s' % ' '.join('%s:%s' % kv for kv in sorted(res.items()) if kv[1] != 'lose'))
        return
    extra = ' '.join('%s:%s' % kv for kv in sorted(res.items()) if kv[1] not in ('lose', 'win'))
    print(indent + 'solver wins by: %s %s' % (' '.join(wins), ('[also ' + extra + ']') if extra else ''))
    if depth >= maxdepth:
        return
    if len(wins) > maxwins:
        print(indent + '  (many winning moves)')
        return
    for m in wins:
        if m == 'pass':
            continue
        nb = after(board, m, solver)
        ok, th = threats(prob, nb, solver, objective)
        if not ok:
            print(indent + '  %s%s: NOT OK (opponent refutes)' % (CNAME[solver], m))
        if not th:
            print(indent + '  %s%s -> no threats (endpoint)' % (CNAME[solver], m))
            continue
        print(indent + '  %s%s -> threats: %s' % (CNAME[solver], m, ' '.join('%s[%s]' % (om, ','.join(w3)) for om, w3, _, _ in th)))
        for om, w3, nb2, lab in th:
            print(indent + '    %s%s %s%s:' % (CNAME[solver], m, CNAME[opp(solver)], om))
            etree(prob, nb2, solver, objective, maxdepth, depth + 2, indent + '      ', maxwins)


if __name__ == '__main__':
    import designs
    from design import load
    name = sys.argv[1]
    seq = [m for m in (sys.argv[2].split(',') if len(sys.argv) > 2 else []) if m]
    d, prob = load(name)
    b = prob.board.copy()
    c = d['first']
    for m in seq:
        b = after(b, m, c)
        c = opp(c)
    if c == d['solver']:
        etree(prob, b, d['solver'], d['objective'], maxdepth=int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    else:
        ok, th = threats(prob, b, d['solver'], d['objective'])
        print('ok', ok)
        for om, w3, nb2, lab in th:
            print('  threat %s -> solver answers %s' % (om, w3))


def solver_tries(prob, board, solver, objective):
    """Solver to move in a lost position. Return solver moves that are threats (opponent must answer),
    with opponent's refuting answers."""
    res = labels(prob, board, solver, solver, objective)
    if '*settled*' in res:
        return []
    o = opp(solver)
    out = []
    for m in sorted(res):
        if m == 'pass':
            continue
        try:
            nb = after(board, m, solver)
        except IllegalMove:
            continue
        nbt = nb.copy()
        nbt.ko = None
        # if opponent ignores, solver moves again: does solver win?
        st = stat(prob, nbt, solver, solver, objective)
        if st == 'win':
            r2 = labels(prob, nb, o, solver, objective)
            if '*settled*' in r2:
                continue
            refs = sorted(k for k, v in r2.items() if v == 'lose')
            kos = sorted(k for k, v in r2.items() if v == 'ko')
            out.append((m, refs, kos))
    return out


def wrong_report(prob, board, seq_first, seq, solver, objective):
    b = board.copy()
    c = seq_first
    for m in seq:
        b = after(b, m, c)
        c = opp(c)
    if c != solver:
        print('position after seq has opponent to move')
        return
    st = stat(prob, b, solver, solver, objective)
    print('status with solver to move:', st)
    for m, refs, kos in solver_tries(prob, b, solver, objective):
        print('  solver try %s -> opponent refutes with %s %s' % (m, refs, ('ko:' + ','.join(kos)) if kos else ''))
