"""Crisp essential-tree metric based on strong threats (<= maxans answers)."""
from gotools import *
import etree


def crisp(prob, board, solver, objective, depth=0, maxdepth=14, maxans=2, budget=[0]):
    """Solver to move. Returns (maxdepth_plies, nodes, maxwins) of the crisp tree."""
    res = etree.labels(prob, board, solver, solver, objective)
    if '*settled*' in res:
        return 0, 0, 0
    wins = [m for m in etree.winning(res) if m != 'pass']
    if not wins:
        return -99, 0, 0
    D, S, MW = 0, 0, len(wins)
    for m in wins:
        nb = etree.after(board, m, solver)
        ok, th = etree.threats(prob, nb, solver, objective)
        strong = [(om, w3, nb2) for om, w3, nb2, lab in th if len([w for w in w3 if w != 'pass']) <= maxans]
        d, s = 1, 1
        if depth + 2 <= maxdepth:
            for om, w3, nb2 in strong:
                d2, s2, mw2 = crisp(prob, nb2, solver, objective, depth + 2, maxdepth, maxans)
                d = max(d, 1 + 1 + d2)
                s += 1 + s2
                MW = max(MW, mw2)
        D = max(D, d)
        S += s
    return D, S, MW
