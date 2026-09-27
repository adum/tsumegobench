"""Auto-generate wrong-move branches: refutation + one level of solver tries with unique refutations."""
import gotools
from gotools import *
import etree


def refute(prob, board, solver, objective, m, prefer=None):
    """Solver played wrong move m. Return (refutation, label) choosing clean refutations first."""
    o = opp(solver)
    nb = etree.after(board, m, solver)
    r2 = etree.labels(prob, nb, o, solver, objective)
    if '*settled*' in r2:
        return None, None, nb
    loses = sorted(k for k, v in r2.items() if v in ('lose', 'lose?') and k != 'pass')
    kos = sorted(k for k, v in r2.items() if v == 'ko' and k != 'pass')
    sekis = sorted(k for k, v in r2.items() if v == 'seki' and k != 'pass')
    order = ((loses, 'lose'), (sekis, 'seki'), (kos, 'ko')) if objective == 'kill' else \
        ((loses, 'lose'), (kos, 'ko'), (sekis, 'seki'))
    for cand, lab in order:
        if cand:
            if prefer:
                for p in prefer:
                    if p in cand:
                        return p, lab, nb
            return cand[0], lab, nb
    return None, None, nb


def wrong_branch(prob, board, solver, objective, m, prefer=None, extend=True):
    ref, lab, nb = refute(prob, board, solver, objective, m, prefer)
    if ref is None:
        return None
    sc, oc = CNAME[solver], CNAME[opp(solver)]
    nb2 = etree.after(nb, ref, opp(solver))
    comment = 'C[Ko]' if lab == 'ko' else ('C[Seki]' if lab == 'seki' else '')
    s = ';%s[%s];%s[%s]%s' % (sc, m, oc, ref, comment)
    if extend and lab == 'lose':
        tries = etree.solver_tries(prob, nb2, solver, objective)
        subs = []
        for t, refs, kos in tries:
            if len(refs) == 1:
                subs.append('(;%s[%s];%s[%s])' % (sc, t, oc, refs[0]))
        if subs:
            s += ''.join(subs)
    return '(' + s + ')', lab
