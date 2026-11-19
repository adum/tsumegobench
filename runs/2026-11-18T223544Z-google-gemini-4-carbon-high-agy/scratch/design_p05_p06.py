#!/usr/bin/env python3
"""Design and verify 5-9 kyu candidates:
- problem-05: Black to play and KILL via sacrifice / under-the-stones / squeeze (bottom-left, 7-9 moves)
- problem-06: White to play and KILL an enclosed CENTER Black group (rows f..m, cols f..m, 5-7 moves)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, iter_components, opp_color, play_move, sgf_to_pt


def test_candidate(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, extra_cap: list[str] = ()):
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

    spec = TsumegoSpec(
        black=b, white=w, first_player=first, defender=defender,
        target_stones=def_stones, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=24)
    opp = opp_color(first)
    opp_v = sol.evaluate(b, w, opp)
    mvs = sol.analyze_moves(b, w, first)
    if not mvs:
        return None, None
    bv = mvs[0][1]
    wins = [m for m, v in mvs if v == bv]
    print(f"=== {name} (stones={(b|w).bit_count()}, empty={empty_c.bit_count()}, cap={cap_mask.bit_count()}) ===")
    print(f"  Opp-first: {TsumegoSolver.OUTCOME_NAMES[opp_v]} | Best: {TsumegoSolver.OUTCOME_NAMES[bv]} | Wins: {wins}")
    print(f"  All 1st moves: {[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in mvs]}")
    if len(wins) == 1 and opp_v != bv:
        # Trace main line up to depth 9!
        def trace(cb, cw, cko, side, depth, prefix):
            if depth > 9:
                return
            cmvs = sol.analyze_moves(cb, cw, side, cko)
            if side == first:
                cwins = [m for m, v in cmvs if v == bv]
                print(f"{'  '*depth}{prefix} -> {first} wins: {cwins}")
                for m in cwins[:2]:
                    nb, nw, nko = play_move(cb, cw, side, sgf_to_pt(m), cko)
                    # Check if ant still has a move that threatens to break bv if prot passed!
                    threats = []
                    for am, av in sol.analyze_moves(nb, nw, opp, nko):
                        nb2, nw2, nko2 = play_move(nb, nw, opp, sgf_to_pt(am), nko)
                        if sol.evaluate(nb2, nw2, opp, None) != bv:
                            threats.append((am, nb2, nw2, nko2))
                    if threats and depth < 9:
                        for am, nb2, nw2, nko2 in threats[:3]:
                            trace(nb2, nw2, nko2, first, depth + 2, f"{first}[{m}]->{opp}[{am}]")
                    else:
                        print(f"{'  '*(depth+1)}{first}[{m}] SETTLES! (0 real threats left)")
        m1 = wins[0]
        nb, nw, nko = play_move(b, w, first, sgf_to_pt(m1))
        for am, av in sol.analyze_moves(nb, nw, opp, nko):
            nb2, nw2, nko2 = play_move(nb, nw, opp, sgf_to_pt(am), nko)
            if sol.evaluate(nb2, nw2, opp, None) != bv:
                trace(nb2, nw2, nko2, first, 2, f"1.{first}[{m1}]->2.{opp}[{am}]")
    return spec, sol


if __name__ == "__main__":
    # --- P05: Bottom-left under-the-stones / sacrifice squeeze (Black to play and KILL White, 7-9 moves) ---
    # How under-the-stones works cleanly:
    # White has 1 real eye at {as} (`ar=O, br=O, bs=O` -> `{as}` is 1 eye!).
    # Connected to `br`, White has `cq, dq, eq, er, es`? Wait:
    # Suppose Black has 2 stones ALREADY inside (`cr=X, dr=X`), and White surrounds them on top (`cp=O, dp=O`? No, White is inside Black's outer wall!).
    # Look! White is enclosed in bottom-left `a..f, o..s` by Black's outer wall `ao, bo, co, do, eo, fp, fq, fr, fs`!
    # Inside:
    #   White has eye #1 at `{ap}`? Let's put eye #1 at `{aq}`: `ap=O, bp=O, bq=O, ar=O, br=O` (`ao..fo=X` above `ap`? Wait: if `ap=O`, `ao=X` touches `ap`, `{aq}` is surrounded by `ap=O, bq=O, ar=O` = 1 real eye!).
    #   Now on rows r, s (`a..e`):
    #   Suppose Black has sacrificial stones `cr=X` (or `cs=X, dr=X`), and when Black extends to 3 stones (`cr, dr, ds` or `bs, cs, ds`), White MUST capture those 3 stones (`W[es]` or `W[bs]`), leaving `{bs, cs, ds}` empty — AND THEN Black plays back at `cs` putting `W[bs]` (or `W[cq]`) in atari so `{bs, cs, ds}` becomes a FALSE eye instead of a 2nd eye!!
    # LET'S TRACE THAT EXACT UNDER-THE-STONES GEOMETRY!!
    # Look at `bs=O`? No: if White captures 3 Black stones `{cs, ds, dr}` by playing `W[es]`:
    # For `5. B[ds]` (playing back inside `{cs, ds, dr}`!) to put a White stone in ATARI:
    # `W[es]` (which JUST captured `{cs, ds, dr}`!) must ONLY have 1 stone (or 2 stones `er, es`) whose ONLY liberties after capturing `{cs, ds, dr}` are `{dr}` and `{ds}`!!
    # CHECK THAT!!
    # Suppose `er=O` (`fr=X, fs=X` on the right! `eq=X` ABOVE `er`!!):
    # LOOK AT `er = O` WITH `eq = X, fr = X, fs = X`!!
    # `er = O` is CUT OFF from White's main body (`ap, bp, bq, cq, dq, ar, br`!) EXCEPT via `dr` and `es`!
    # Initially:
    #   `dr = X` (Black stone inside!), `cs = .`, `ds = .`, `es = .`, `bs = O` (connected to `br=O`!)!
    #   Wait: check liberties of `dr = X`: `dq=O` (top), `cr=O`? If `cr=O`, `dr=X` has ONLY `ds(.)`! Give `cr = .`!
    #   Let's test 3 exact variations of this bottom-left under-the-stones setup!
    test_candidate("P05-ishi-1", [
        "XXXXXX,",  # o(14): ao..fo = X
        "OOXXXX,",  # p(15): ap=O, bp=O, cp=X, dp=X, ep=X, fp=X
        ".OOOXX,",  # q(16): aq=., bq=O, cq=O, dq=O, eq=X, fq=X
        "OO.XOX,",  # r(17): ar=O, br=O, cr=., dr=X, er=O, fr=X
        "OO...X,",  # s(18): as=O, bs=O, cs=., ds=., es=., fs=X
    ], r0=14, c0=0, first="B", defender="W", extra_cap=["dr", "er"])

    test_candidate("P05-ishi-2", [
        "XXXXXXX",  # o(14): ao..go = X
        "OOXXXXX",  # p(15): ap=O, bp=O, cp..gp = X
        ".OOOOXX",  # q(16): aq=., bq=O, cq=O, dq=O, eq=O, fq=X, gq=X
        "OO..XOX",  # r(17): ar=O, br=O, cr=., dr=., er=X, fr=O, gr=X
        "OOO...X",  # s(18): as=O, bs=O, cs=O, ds=., es=., fs=., gs=X
    ], r0=14, c0=0, first="B", defender="W", extra_cap=["er", "fr"])

    test_candidate("P05-ishi-3", [
        "XXXXXXX",  # o(14)
        "OO.XXXX",  # p(15): ap=O, bp=O, cp=., dp..gp=X? Keep cp=X!
    ][:1] + [
        "OOXXXXX",  # p(15)
        ".OOOXXX",  # q(16): aq=., bq=O, cq=O, dq=O, eq=X, fq=X, gq=X
        "OO..XOX",  # r(17): ar=O, br=O, cr=., dr=., er=X, fr=O, gr=X
        "OO....X",  # s(18): as=O, bs=O, cs=., ds=., es=., fs=., gs=X
    ], r0=14, c0=0, first="B", defender="W", extra_cap=["er", "fr"])

    # --- P06: Pure CENTER enclosed Black group, White to play and KILL (rows f..m, cols f..m) ---
    # Black group in the center surrounded by a solid White ring!
    test_candidate("P06-center-1", [
        ",OOOOO,",  # f(5): gf..kf = O
        "OOXXXOO",  # g(6): fg=O, gg=O, hg=X, ig=X, jg=X, kg=O, lg=O
        "OX.O.XO",  # h(7): fh=O, gh=X, hh=., ih=O, jh=., kh=X, lh=O
        "OXX.XXO",  # i(8): fi=O, gi=X, hi=X, ii=., ji=X, ki=X, li=O
        "OX...XO",  # j(9): fj=O, gj=X, hj=., ij=., jj=., kj=X, lj=O
        "OOXXXOO",  # k(10): fk=O, gk=O, hk=X, ik=X, jk=X, kk=O, lk=O
        ",OOOOO,",  # l(11): gl..kl = O
    ], r0=5, c0=5, first="W", defender="B", extra_cap=["ih"])

    test_candidate("P06-center-2 (asymmetric center)", [
        ",,OOOO,",  # f(5): hf..kf = O
        ",OXXXOO",  # g(6): gg=O, hg=X, ig=X, jg=X, kg=O, lg=O
        "OX.X.XO",  # h(7): fh=O, gh=X, hh=., ih=X, jh=., kh=X, lh=O  (hh is 1 real eye if gh,hg,ih,hi=X!)
        "OXX.XXO",  # i(8): fi=O, gi=X, hi=X, ii=., ji=X, ki=X, li=O
        "OO...XO",  # j(9): fj=O, gj=O, hj=., ij=., jj=., kj=X, lj=O
        ",OXXXOO",  # k(10): gk=O, hk=X, ik=X, jk=X, kk=O, lk=O
        ",,OOOO,",  # l(11): hl..kl = O
    ], r0=5, c0=5, first="W", defender="B")

    test_candidate("P06-center-3 (asymmetric center peep + throw-in)", [
        ",,OOOO,",  # f(5): hf..kf = O
        ",OXXXOO",  # g(6): gg=O, hg=X, ig=X, jg=X, kg=O, lg=O
        "OX.X.OO",  # h(7): fh=O, gh=X, hh=., ih=X, jh=., kh=O, lh=O  (eye 1 at hh!)
        "OXXXXXO",  # i(8): fi=O, gi=X, hi=X, ii=X, ji=X, ki=X, li=O
        "OO..XXO",  # j(9): fj=O, gj=O, hj=., ij=., jj=X, kj=X, lj=O
        ",OX.XOO",  # k(10): gk=O, hk=X, ik=., jk=X, kk=O, lk=O
        ",OOXOO,",  # l(11): gl=O, hl=O, il=X, jl=O, kl=O
        ",,,O,,,",  # m(12): im=O? Wait il=X would have 1 lib ik! Give im=., in=O, hm=O, jm=O!
    ][:7] + [
        ",,O.O,,",  # m(12): hm=O, im=., jm=O
        ",,,O,,,",  # n(13): in=O
    ], r0=5, c0=5, first="W", defender="B")
