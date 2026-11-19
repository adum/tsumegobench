#!/usr/bin/env python3
"""
Find exact 5-move unique-solution problems for:
- problem-03.sgf (10-19 kyu, Black to play and kill, 5 moves)
- problem-04.sgf (10-19 kyu, White to play and live, 5 moves)
"""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, benson_alive_mask, dilate, iter_components, opp_color, play_move, pt_to_sgf, sgf_to_pt


def min_plies_to_settle(spec: TsumegoSpec, sol: TsumegoSolver, b: int, w: int, side: str, ko: int | None, target_v: int, depth: int = 0) -> int:
    """Compute exact minimax length of main line until outcome is trivially settled (even if protagonist passes!)."""
    prot = spec.first_player
    ant = opp_color(prot)
    # Check if already settled even if protagonist does nothing (antagonist gets a free move!)
    if side == ant:
        # Just played a protagonist move: is it already settled?
        # For LIVE (target_v == 4): settled when is_defender_clean_alive(b, w) OR even if ant plays ANY move and gets another move?
        # Wait: in GoProblems, a LIVE line ends on protagonist's move when either:
        #   - benson_alive_mask already holds, OR every antagonist reply has >=3 trivial winning answers / dead stones need no capture!
        # Strict check: if ant passes/plays, can ant force protagonist to respond?
        # Check if there exists ANY ant move `m2` after which protagonist passing would FAIL (`sol.evaluate(after_m2, side=ant) != target_v`)!
        has_real_threat = False
        for m2, v2 in sol.analyze_moves(b, w, ant, ko):
            nb, nw, nko = play_move(b, w, ant, sgf_to_pt(m2), ko)
            # If protagonist passed here (meaning ant gets to move AGAIN with ko cleared!), would ant break target_v?
            if sol.evaluate(nb, nw, ant, None) != target_v:
                has_real_threat = True
                break
        if not has_real_threat or depth >= 13:
            return depth

    if depth >= 13:
        return depth

    mvs = sol.analyze_moves(b, w, side, ko)
    if side == prot:
        best = [m for m, v in mvs if v == target_v]
        if not best:
            return depth
        return min(
            min_plies_to_settle(spec, sol, *play_move(b, w, side, sgf_to_pt(m), ko), target_v, depth + 1)
            for m in best[:3]
        )
    else:
        # Antagonist maximizes plies needed to settle!
        real_defs = []
        for m2, v2 in mvs:
            nb, nw, nko = play_move(b, w, ant, sgf_to_pt(m2), ko)
            if sol.evaluate(nb, nw, ant, None) != target_v:
                real_defs.append((nb, nw, nko))
        if not real_defs:
            return depth
        return max(
            min_plies_to_settle(spec, sol, nb, nw, prot, nko, target_v, depth + 1)
            for nb, nw, nko in real_defs[:4]
        )


def check_grid(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, extra_cap: list[str] = ()):
    b = w = empty_c = 0
    for dr, row_s in enumerate(grid):
        row = row_s.replace(" ", "")
        for dc, ch in enumerate(row):
            pt = (r0 + dr) * 19 + (c0 + dc)
            if ch == "X":
                b |= 1 << pt
            elif ch == "O":
                w |= 1 << pt
            elif ch == ".":
                empty_c |= 1 << pt
    def_stones = b if defender == "B" else w
    att_stones = w if defender == "B" else b
    cap_mask = sum(1 << sgf_to_pt(s) for s in extra_cap)
    for ch in iter_components(def_stones):
        if ch.bit_count() <= 4:
            cap_mask |= ch
    imm_att = att_stones & ~cap_mask
    combat = empty_c | cap_mask
    outside = BOARD_MASK ^ (empty_c | def_stones | cap_mask)
    spec = TsumegoSpec(black=b, white=w, first_player=first, defender=defender,
                       target_stones=def_stones, combat_mask=combat,
                       outside_mask=outside, immortal_attacker=imm_att)
    sol = TsumegoSolver(spec, max_depth=22)
    opp = opp_color(first)
    opp_v = sol.evaluate(b, w, opp)
    mvs = sol.analyze_moves(b, w, first)
    if not mvs:
        return
    bv = mvs[0][1]
    wins = [m for m, v in mvs if v == bv]
    settled_len = min_plies_to_settle(spec, sol, b, w, first, None, bv) if len(wins) <= 2 else -1
    print(f"{name:28s}: opp1st={TsumegoSolver.OUTCOME_NAMES[opp_v]:10s} best={TsumegoSolver.OUTCOME_NAMES[bv]:10s} wins={wins} len={settled_len} | all={[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m,v in mvs]}")
    if len(wins) == 1 and opp_v != bv:
        m1 = wins[0]
        nb, nw, nko = play_move(b, w, first, sgf_to_pt(m1))
        for m2, v2 in sol.analyze_moves(nb, nw, opp, nko):
            nb2, nw2, nko2 = play_move(nb, nw, opp, sgf_to_pt(m2), nko)
            r3 = [(m3, TsumegoSolver.OUTCOME_NAMES[v3]) for m3, v3 in sol.analyze_moves(nb2, nw2, first, nko2) if v3 == bv]
            print(f"   1.{first}[{m1}] -> 2.{opp}[{m2}] -> 3.{first} wins: {[x[0] for x in r3]}")


if __name__ == "__main__":
    print("=== P03 CANDIDATES (10-19k, Black to play and KILL in 5 moves) ===")
    # Theme: Throw-in on 1st line to falsify eye + vital point / snapback!
    # Top edge, cols d(3)..l(11), rows a(0)..d(3):
    # White has 1 eye on right {ja}, and on left {fa, gb, hb} where Black throws in `1. B[fa]` -> `2. W[ga]` captures?
    # Let's construct carefully:
    # Suppose `ea=X` (connected to `eb=X`), `fa=.`, `ga=O`? If `ea=X`, `1. B[fa]` isn't a throw-in, it's connected to `ea`!
    # For `1. B[fa]` to be a THROW-IN, `ea` is `O` (with 2 liberties `da`? No: `da=X`, `ea=O`, `fa=.`, `ga=O`, `eb=X`, `fb=X`!):
    # TRACE `da=X, eb=X, fb=X` surrounding `ea=O`!!
    # `ea=O` has ONLY 1 liberty `fa`? No, give `ea=O` 1 stone `ea=O` -> if `eb=O`, `ea-eb` has `fa` and `fb`;
    # Instead: `da=X, db=X, ec=X, fc=X`, and `ea=O, eb=O`, `fa=.`, `fb=O`? No: `ea=O`, `eb=.`, `fa=.`, `fb=O`!
    # Look at `ea=O` (`(a,e)`): neighbors `da(X)`, `fa(.)`, `eb(.)` -> 2 liberties!
    # Even cleaner: `fb = X` (peeping from below!), `ea = O`? No, if `fb=X` and `da=X`, `ea` has `eb`? `ea`'s neighbors are `da(X), fa(.), eb(.)` — wait `(b,e)` is `eb`, `(b,f)` is `fb`!
    # Let's test 4 throw-in + vital-point kill shapes!
    check_grid("P03-kill-1 (throw-in + nakade)", [
        "XO.O..O.OX",  # a: ca=X, da=O, ea=., fa=O, ga=., ha=., ia=O, ja=., ka=O, la=X? (10 cols c..l)
        "XXO.OOOOX,",  # b: cb=X, db=X, eb=O, fb=., gb=O, hb=O, ib=O, jb=O, kb=X
        ",XXOOOOXX,",  # c: dc=X, ec=X, fc=O, gc=O, hc=O, ic=O, jc=X, kc=X
        ",,XXXXXX,,",  # d: ed..jd = X
    ], r0=0, c0=2, first="B", defender="W", extra_cap=["da"])

    check_grid("P03-kill-2 (throw-in + vital)", [
        "XO.O..OX",    # a(0): da=X, ea=O, fa=., ga=O, ha=., ia=., ja=O, ka=X  (8 cols d..k)
        "XXO..OOX",    # b(1): db=X, eb=X, fb=O, gb=., hb=., ib=O, jb=O, kb=X
        ",XXOOOOX",    # c(2): ec=X, fc=X, gc=O, hc=O, ic=O, jc=O, kb/kc=X
        ",,XXXXXX",    # d(3): fd..kd = X
    ], r0=0, c0=3, first="B", defender="W", extra_cap=["ea"])

    check_grid("P03-kill-3 (snapback + eye kill)", [
        "X.O..O.OX",   # a(0): da=X, ea=., fa=O, ga=., ha=., ia=O, ja=., ka=O, la=X (9 cols d..l)
        "XXO.OOOOX",   # b(1): db=X, eb=X, fb=O, gb=., hb=O, ib=O, jb=O, kb=O, lb=X
        ",XXXOOXXX",   # c(2): ec=X, fc=X, gc=X, hc=O, ic=O, jc=X, kc=X, lc=X
        ",,,XXXX,,",   # d(3): gd..jd = X
    ], r0=0, c0=3, first="B", defender="W", extra_cap=["fa", "fb"])

    check_grid("P03-kill-4 (wedge + shortage)", [
        "X..OO.OX",    # a(0): da=X, ea=., fa=., ga=O, ha=O, ia=., ja=O, ka=X
        "XXO..OOX",    # b(1): db=X, eb=X, fb=O, gb=., hb=., ib=O, jb=O, kb=X
        ",XXOOOOX",    # c(2): ec=X, fc=X, gc=O, hc=O, ic=O, jc=O, kc=X
        ",,XXXXXX",    # d(3): fd..kd = X
    ], r0=0, c0=3, first="B", defender="W", extra_cap=["fb"])

    print("\n=== P04 CANDIDATES (10-19k, White to play and LIVE in 5 moves on right edge) ===")
    # Adapt the 5-move 1st-line expansion + eye-making logic onto the right edge with an asymmetric hook!
    check_grid("P04-live-1", [
        ",,XX",  # d(3): rd=X, sd=X
        ",XX.",  # e(4): qe=X, re=X, se=.
        ",XO.",  # f(5): qf=X, rf=O, sf=.
        "XXO.",  # g(6): pg=X, qg=X, rg=O, sg=.
        "XO.O",  # h(7): ph=X, qh=O, rh=., sh=O
        "XOO.",  # i(8): pi=X, qi=O, ri=O, si=.
        "XXOO",  # j(9): pj=X, qj=X, rj=O, sj=O
        ",XXX",  # k(10): qk=X, rk=X, sk=X
    ], r0=3, c0=15, first="W", defender="W", extra_cap=["sd"])

    check_grid("P04-live-2", [
        ",,,XX", # d(3): rd=X, sd=X
        ",,XO.", # e(4): qe=X, re=O, se=.
        ",XXO.", # f(5): pf=X, qf=X, rf=O, sf=.
        "XXO..", # g(6): og=X, pg=X, qg=O, rg=., sg=.
        "XO..O", # h(7): oh=X, ph=O, qh=., rh=., sh=O
        "XOOOX", # i(8): oi=X, pi=O, qi=O, ri=O, si=X
        ",XXXX", # j(9): pj..sj = X
    ], r0=3, c0=14, first="W", defender="W", extra_cap=["si"])

    check_grid("P04-live-3", [
        ",,XX",  # d(3): rd=X, sd=X
        ",XO.",  # e(4): qe=X, re=O, se=.
        ",XO.",  # f(5): qf=X, rf=O, sf=.
        "XXO.",  # g(6): pg=X, qg=X, rg=O, sg=.
        "XO..",  # h(7): ph=X, qh=O, rh=., sh=.
        "XOO.",  # i(8): pi=X, qi=O, ri=O, si=.
        ",XXO",  # j(9): qj=X, rj=X, sj=O
        ",,XX",  # k(10): rk=X, sk=X
    ], r0=3, c0=15, first="W", defender="W", extra_cap=["sj"])
