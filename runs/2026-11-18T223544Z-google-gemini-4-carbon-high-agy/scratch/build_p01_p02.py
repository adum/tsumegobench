#!/usr/bin/env python3
"""Construct and test P01 (25-28k B live, 3-move right-direction atari) and P02 (21-24k W kill, 3-move wedge)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fast_explore import eval_grid

if __name__ == "__main__":
    # === P01: Black to play and live (~26 kyu) ===
    # Left edge, rows d(3)..l(11), cols a(0)..e(4):
    # Top wing of Black has 1 real eye at af:
    #   d: O O O , ,
    #   e: X X O , ,
    #   f: . X O , ,   <-- 1 real eye at af!
    #   g: X X X O ,
    # Middle has a cutting White stone O[bh] with 2 liberties (ah and bi)!
    # Wait: if B plays B[bi] (atari from the open/wall side!), W[ah] tries to flee to 1st line -> B[ai] captures O[bh,ah]!
    #Whereas if B plays B[ah] (atari from 1st line!), W[bi] connects O[bh] to O[ci] (White's outer wall!!) -> Black's bottom stones die and Black only has 1 eye {af}!
    # Let's check!! Make ci=O? Wait: if ci=O is ALREADY there, then B[bi] puts B[bi] next to ci=O!
    # Let's check liberties of B[bi]: if bj=X, aj=X (bottom Black stones!), then B[bi] connects to bj=X!
    # Let's trace!!
    #   d: O O O , ,   (ad=O, bd=O, cd=O)
    #   e: X X O , ,   (ae=X, be=X, ce=O)
    #   f: . X O , ,   (af=., bf=X, cf=O)
    #   g: X X O O ,   (ag=X, bg=X, cg=O, dg=O)
    #   h: . O . O ,   (ah=., bh=O, ch=., dh=O)  <-- O[bh] has 2 libs: ah and ch? Wait: if bi=X, then O[bh] has libs ah and ch!
    #   LOOK AT THAT:
    #   If h row is: ah=., bh=O, ch=., dh=O
    #   and i row is: ai=X, bi=X, ci=X, di=O
    #   and j row is: aj=O, bj=O, cj=O
    #   TRACE O[bh]!!
    #   O[bh] has TWO liberties: `ah` (1st line!) and `ch` (toward White's wall `dh=O, cg=O`!!)!
    #   1) If Black plays `1. B[ch]` (wedging between O[bh] and White's wall `cg, dh`!!):
    #      - Wait: `B[ch]` connects to `ci=X`! So `B[ch]` is NOT captured — `ai-bi-ci-ch` has liberty `ah`? Wait: `ai-bi-ci` needs another liberty so `B[ch]` isn't self-atari! Give `ai-bi-ci` liberty `aj=.` (`ak=X, bk=X`? Or `ai=., bi=X, ci=X`!).
    #      LET'S TRACE `ai=., bi=X, ci=X`!!
    #      - `bi-ci` has liberty `ai` AND `ch`!
    #      - `1. B[ch]` connects to `ci`, has liberty `ai`, AND puts `O[bh]` in **ATARI** at `ah`!
    #      - `2. W[ah]` extends onto 1st line (`ah-bh` now has ONLY 1 liberty `ai`!!)!
    #      - `3. B[ai]C[RIGHT]` **CAPTURES BOTH `W[ah]` AND `W[bh]`**, connecting top and bottom and making a huge 2nd eye!!
    #      - WHEREAS if Black plays `1. B[ah]` (wrong-direction atari from 1st line!):
    #        `2. W[ch]` connects `O[bh]` to `cg=O, dh=O` (White's immortal outer wall!!), cutting off `bi-ci` (which dies!) and leaving top Black with ONLY 1 eye `{af}` -> **DEAD**!!
    #      - AND if Black plays `1. B[ai]`: `2. W[ch]` connects out -> **DEAD**!!
    eval_grid("P01-edge-atari", [
        "OOO,,",  # d(3): ad=O, bd=O, cd=O
        "XXO,,",  # e(4): ae=X, be=X, ce=O
        ".XO,,",  # f(5): af=., bf=X, cf=O
        "XXOO,",  # g(6): ag=X, bg=X, cg=O, dg=O
        ".O.O,",  # h(7): ah=., bh=O, ch=., dh=O
        ".XXO,",  # i(8): ai=., bi=X, ci=X, di=O
        "OOOO,",  # j(9): aj=O, bj=O, cj=O, dj=O
    ], r0=3, c0=0, first="B", defender="B", capturable_coords=["bh"])

    # === P02: White to play and kill (~22 kyu) ===
    # Bottom-right side (away from corner! cols i(8)..q(16), rows p(15)..s(18)):
    # Black has 1 real eye on right {os} (nr,ns,or,pr,ps? Wait: on row s, `os` surrounded by `ns=X, or=X, ps=X` is 1 real eye!).
    # On left wing, Black wants a 2nd eye at {ks} or {lr}, separated by a diagonal defect!
    eval_grid("P02-wedge-kill", [
        ",,,OOOOO,",  # p(15): lp=O, mp=O, np=O, op=O, pp=O
        ",OOXXXXOO",  # q(16): jq=O, kq=O, lq=X, mq=X, nq=X, oq=X, pq=O, qq=O
        "OX..XXXXO",  # r(17): ir=O, jr=X, kr=., lr=., mr=X, nr=X, or=X, pr=X, qr=O
        "OXX..X.XO",  # s(18): is=O, js=X, ks=., ls=., ms=X, ns=X? Wait: make os=. (ns=X, os=., ps=X)!
    ][:3] + [
        "OXX.XX.XO",  # s(18): is=O, js=X, ks=., ls=X, ms=X, ns=X? Wait: i,j,k,l,m,n,o,p,q = 9 cols!
        # i=O, j=X, k=X, l=., m=X, n=X, o=., p=X, q=O!
        # Let's check cols: i(0), j(1), k(2), l(3), m(4), n(5), o(6), p(7), q(8):
        # r: i=O, j=X, k=., l=., m=X, n=X, o=X, p=X, q=O
        # s: i=O, j=X, k=X, l=., m=X, n=X, o=., p=X, q=O
    ], r0=15, c0=8, first="W", defender="B")

    # Also test a variant of P02 where W plays vital throw-in/wedge with 2 distinct B replies!
    eval_grid("P02-wedge-kill-2", [
        ",,OOOOO,,",  # p(15): kp..op = O
        ",OXXXXXOO",  # q(16): jq=O, kq=X, lq=X, mq=X, nq=X, oq=X, pq=O, qq=O
        "OX.O.XXXO",  # r(17): ir=O, jr=X, kr=., lr=O, mr=., nr=X, or=X, pr=X, qr=O
        "OX...X.XO",  # s(18): is=O, js=X, ks=., ls=., ms=., ns=X, os=., ps=X, qr/qs=O
    ], r0=15, c0=8, first="W", defender="B", capturable_coords=["lr"])
