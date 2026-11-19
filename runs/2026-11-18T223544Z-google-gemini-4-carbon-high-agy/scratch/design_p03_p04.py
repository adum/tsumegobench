#!/usr/bin/env python3
"""Design 5-move 10-19 kyu candidates for problem-03 (B to play) and problem-04 (W to play)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# First bump cap_mask threshold in fast_explore to 6 stones so 4-6 stone chains are also tracked after capture
fe_path = Path(__file__).resolve().parent / "fast_explore.py"
fe_txt = fe_path.read_text()
if "ch.bit_count() <= 3" in fe_txt:
    fe_path.write_text(fe_txt.replace("ch.bit_count() <= 3", "ch.bit_count() <= 6"))

from fast_explore import eval_grid
from go_engine import play_move, sgf_to_pt, TsumegoSolver

if __name__ == "__main__":
    # === P03 (12-16 kyu, Black to play and LIVE in 5 moves on top edge) ===
    # Extend our P01-GEM idea by 2 moves!
    # How? Before B[ma] works, suppose White has a stone O[na]? No:
    # Suppose on the left of `ma`, `la` is EMPTY, `ka=O`, and if B plays `1. B[la]`? Earlier `la=.` let `ma` and `mb` also work.
    # Instead, what if `1. B[pa]` (capturing or threatening on right) -> `2. W[qa]` -> `3. B[ma]` -> `4. W[kc]` -> `5. B[mb]`!
    # Look! Suppose on the right wing, White has a stone `pb = O`? No:
    # Suppose on the right wing, `pa` is `X`, `qa` is `.`, `ra` is `.`, `sa` is `O`, `qb` is `X`, `rb` is `O`:
    # Wait: if `pa=., qa=X, ra=., sa=O` and `ob=X, pb=X, qb=., rb=O`:
    # Look at `qa=X` (1st line): `qa` has libs `pa, ra, qb`.
    # Even simpler! Look at `kc` on the left wing of P01-GEM:
    # What if `kb-lb-lc-mc` has a 2-step squeeze before `mb` is needed:
    #   a: O O O . . X . X O   (j..r)
    #   b: O . X . X X X X O   (jb=O, kb=., lb=X, mb=., nb=X...)
    #   c: O X X X O O O O O   (jc=O, kc=X, lc=X, mc=X, nc=O...)
    #   d: , O O O O , , , ,
    # Check what happens when `kb = .` and `lb, kc, lc, mc` is Black!
    # Wait: `kb` has `ka=O, jb=O, lb=X, kc=X` -> `{kb}` is a false eye! Same 3 moves!
    # Now make `{jb, kb}` a 2-stone throw-in / hane squeeze:
    #   a: O O O . . X . X O   (ja=O, ka=O, la=O, ma=., na=., oa=X, pa=., qa=X, ra=O)
    #   b: O . X . X X X X O   (jb=O, kb=., lb=X, mb=., nb=X, ob=X, pb=X, qb=X, rb=O)
    #   c: O . X X O O O O O   (jc=O, kc=., lc=X, mc=X, nc=O...)
    # Wait: if BOTH kb=. and kc=., then lb-lc-mc has 3 libs (kb, kc, mb)! Still 5 moves: 1.B[ma] 2.W[kb] 3.B[kc]? Let's test!
    eval_grid("P03-5move-A", [
        "OOO..X.XO",
        "O.X.XXXXO",
        "O.XXOOOOO",
        "OOOO,,,,,",
    ], r0=0, c0=9, first="B", defender="B")

    # Also test a crisp 5-move THROW-IN + VITAL POINT KILL for P03 (Black to kill White on top-left side, ~14 kyu):
    # White has 1 real eye on right, and on left has a tiger's mouth where Black throws in at 1st line, W captures, B plays vital point!
    eval_grid("P03-throwin-kill", [
        "XO.O..O.OX",  # a: da=X, ea=O, fa=., ga=O, ha=., ia=., ja=O, ka=., la=O, ma=X
        "XOOOOOOOX,",  # b: db=X, eb=O, fb=O, gb=O, hb=O? Wait: if eb..kb is all O, {fa} AND {ka} are ALREADY 2 eyes!
    ][:1] + [
        # Make {ka} 1 real eye, and on the left {fa} is FALSIFIABLE via throw-in!
        # Wait: {fa} is falsifiable if `eb` is NOT `O` (`eb = .`, `db = X`, `ec = X`, `fc = O`, `gb = O`):
        # Look at cols d(3)..m(12), rows a..d:
        #   a: X . O . O . . O . X   (da=X, ea=., fa=O, ga=., ha=O, ia=., ja=., ka=O, la=., ma=X? Too wide!)
        # Compact 7-col shape (cols e..k, rows a..d):
        #   a: X . O . O . X   (ea=X, fa=., ga=O, ha=., ia=O, ja=., ka=X)
        #   b: X X O O O O X   (eb=X, fb=X, gb=O, hb=O, ib=O, jb=O, kb=X) -> {ha} is 1 real eye!
        # That's too small. Let's make a 5-move throw-in + nakade kill!
        "X.OO..OX",  # a(0): ea=X, fa=., ga=O, ha=O, ia=., ja=., ka=O, la=X
        "XXO..OOX",  # b(1): eb=X, fb=X, gb=O, hb=., ib=., jb=O, kb=O, lb=X
        ",XXOOOOX",  # c(2): fc=X, gc=X, hc=O, ic=O, jc=O, kc=O, lc=X
        ",,XXXXXX",  # d(3): gd..ld = X
    ], r0=0, c0=4, first="B", defender="W")

    # Test P03-throwin-kill-2:
    eval_grid("P03-throwin-kill-2", [
        "X..O..OX",  # a: ea=X, fa=., ga=., ha=O, ia=., ja=., ka=O, la=X
        "XXOO.OOX",  # b: eb=X, fb=X, gb=O, hb=O, ib=., jb=O, kb=O, lb=X
        ",XXOOOOX",  # c: fc=X, gc=X, hc=O, ic=O, jc=O, kc=O, lc=X
        ",,XXXXXX",  # d
    ], r0=0, c0=4, first="B", defender="W")

    # === P04 (11-14 kyu, White to play and LIVE in 5 moves on right edge, avoiding Ko!) ===
    # Like gp-10507 (13 kyu), where naive moves give Ko or Death, while exact 5-move order makes Clean Life!
    eval_grid("P04-right-live-A", [
        ",,XX",  # e(4): re=X, se=X
        ",XXO",  # f(5): qf=X, rf=X, sf=O
        ",XO.",  # g(6): qg=X, rg=O, sg=.
        ",XO.",  # h(7): qh=X, rh=O, sh=.
        "XXO.",  # i(8): pi=X, qi=X, ri=O, si=.
        "XO..",  # j(9): pj=X, qj=O, rj=., sj=.
        "XOOX",  # k(10): pk=X, qk=O, rk=O, sk=X
        ",XXX",  # l(11): ql=X, rl=X, sl=X
    ], r0=4, c0=15, first="W", defender="W", capturable_coords=["sk"])

    eval_grid("P04-right-live-B", [
        ",,XX",  # e: re=X, se=X
        ",XXO",  # f: qf=X, rf=X, sf=O
        ",XO.",  # g: qg=X, rg=O, sg=.
        "XXO.",  # h: ph=X, qh=X, rh=O, sh=.
        "XO..",  # i: pi=X, qi=O, ri=., si=.
        "XO.O",  # j: pj=X, qj=O, rj=., sj=O
        ",XX.",  # k: qk=X, rk=X, sk=.
        ",,XX",  # l: rl=X, sl=X
    ], r0=4, c0=15, first="W", defender="W")
