#!/usr/bin/env python3
"""
Construct exact causal-chain 7-to-9 move problems for:
- problem-08.sgf (1-4 kyu, White to play and LIVE, stepped bottom-left L-shape, 5-7 forced moves)
- problem-10.sgf (1-2 dan, White to play and KILL, asymmetric floating/side group, 7-9 forced moves)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_dan import eval_dan

if __name__ == "__main__":
    print("=== P08: Stepped Bottom-Left White to LIVE (5-7 forced moves, 1-4 kyu) ===")
    # Causal chain for LIVING:
    # White's bottom wing has 1 eye `{ar, as}` (`br,cr=O, bs,cs=O, aq,bq,cq=O`).
    # White's upper wing (`rows l..p, cols a..d`) needs a 2nd eye at `{am}` (surrounded by `al=O, bm=O, an=O`),
    # EXCEPT `al` and `bm` are empty, `ak..dk = X` on top, and `bn = O, cn = O` is separated from `aq-bq-cq` by `bo = .` (`ao=X`, `co=X`!)!
    # Look! Let's wire a 2-step probe + 5-step miai/shortage on the left wall (cols a..f, rows j..s) — tall stepped shape!
    # Take our proven P04 5-move miai-junction (`rg`), rotate it onto a stepped bottom-left L-wing AND add a 2-move probe!
    # Wait: first check rotated/stepped L-wing with an asymmetric tail so it's 0% similar to P04 AND 5-7 forced moves:
    eval_dan("P08-causal-live-1", [
        ",,XXXX",  # k(10): ck..fk = X
        ",XXO..",  # l(11): bl,cl=X; dl=O; el,fl=.? Wait put edge on LEFT (col a = 1st line!!):
    ][:0] + [
        # Col a is the left 1st line! Rows j(9)..r(17), cols a(0)..f(5):
        "XX,,,",   # j(9): aj,bj = X
        ".OXX,",   # k(10): ak=., bk=O; ck,dk=X
        ".OXX,",   # l(11): al=., bl=O; cl,dl=X
        "..OXX",   # m(12): am,bm=.; cm=O; dm,em=X
        "O..OX",   # n(13): an=O; bn,cm? bn,cn=.; dn=O, en=X
        "XOO.X",   # o(14): ao=X; bo,co=O, do=., eo=X  <-- do=. must be connected or probed!
        "XO.OX",   # p(15): ap=X, bp=O, cp=., dp=O, ep=X
        "XXOOX",   # q(16): aq,bq=X; cq,dq=O, eq=X
        ",,XXX",   # r(17): cr..er = X
    ], r0=9, c0=0, first="W", defender="W", cap_coords=["bk", "bl", "an"])

    # Variant 2 of P08: bottom-left corner + tall left leg (`a..f, l..s`), White to LIVE via 7-move throw-in + squeeze!
    eval_dan("P08-causal-live-2", [
        "XXXX,,",  # l(11): al..dl = X
        ".OXX,,",  # m(12): am=., bm=O; cm,dm=X
        "..OXX,",  # n(13): an,bn=.; cn=O; dn,en=X
        "O.OOXX",  # o(14): ao=O, bo=., co,do=O; eo,fo=X
        "XXO.OX",  # p(15): ap,bp=X; cp=O, dp=., ep=O, fp=X
        ".XOOOX",  # q(16): aq=., bq=X; cq..eq=O, fq=X
        ".OOXXX",  # r(17): ar=.; br,cr=O; dr..fr=X
        "OOOXX,",  # s(18): as..cs=O; ds,es=X
    ], r0=11, c0=0, first="W", defender="W", cap_coords=["bm", "ao", "ap", "bp", "bq"])

    # Variant 3 of P08: fewer cap stones (fast <50ms!) — 1st-line hane probe + belly squeeze!
    eval_dan("P08-causal-live-3", [
        "XXXX,",   # l(11): al..dl = X
        "..XX,",   # m(12): am,bm=.; cm,dm=X
        ".OOXX",   # n(13): an=.; bn,cn=O; dn,en=X
        ".XXOX",   # o(14): ao=.; bo,co=X; do=O, eo=X
        "OO.OX",   # p(15): ap,bp=O, cp=., dp=O, ep=X
        ".OOXX",   # q(16): aq=.; bq,cq=O; dq,eq=X
        ".OOX,",   # r(17): ar=.; br,cr=O; dr=X  ({aq,ar}? as=O closes it!)
        "OOXX,",   # s(18): as,bs=O; cs,ds=X
    ], r0=11, c0=0, first="W", defender="W", cap_coords=["bo", "co"], ignore_pts={"aq", "ar"})

    print("\n=== P10: Causal-Chain 7-9 Move 1-2 Dan White to KILL (center-side / stepped group) ===")
    # Wire the exact 3-stage causal chain `1.W[A] -> 2.B[A'] -> 3.W[B] -> 4.B[B'] -> 5.W[C] -> 6.B[D] -> 7.W[E]`!
    # Look at our floating center group from P06 (`Clean-Minimal-Center`), which killed in 3-4 moves (`1.W[ji] -> 2.B[ii] -> 3.W[ki]`):
    # Why did `1.W[ji]` work immediately in P06? Because `li = O` was ALREADY at `(i, l)`!
    # Suppose in a totally different vertical/diagonal center-right region (cols i..p, rows c..k):
    # Stage 1: White probes `1.W[A]` threatening to cut Black's upper 1-eye block; Black MUST connect `2.B[A']`, filling a liberty of Black's central spine!
    # Stage 2: Because Black's spine lost that liberty, White can NOW wedge/peep `3.W[B]`, forcing `4.B[B']`!
    # Stage 3: Now White plays the vital placement/throw-in `5.W[C]` -> `6.B[D]` -> `7.W[E]C[RIGHT]`!
    eval_dan("P10-causal-kill-1", [
        ",,OOOOO,",  # d(3): kd..od = O
        ",OOXXXOO",  # e(4): je,ke=O; le,me,ne=X; oe,pe=O
        "OOX.X.XO",  # f(5): if,jf=O; kf=X, lf=., mf=X, nf=., of=X, pf=O
        "O.XX..OO",  # g(6): ig=O, jg=.; kg,lg=X; mg,ng=.; og,pg=O
        "OO.XX.XO",  # h(7): ih,jh=O, kh=.; lh,mh=X, nh=., oh=X, ph=O
        ",OOXXXOO",  # i(8): ji,ki=O; li,mi,ni=X; oi,pi=O
        ",,OOOOO,",  # j(9): kj..oj = O
    ], r0=3, c0=8, first="W", defender="B", cap_coords=["kf", "of", "oh"])

    eval_dan("P10-causal-kill-2", [
        ",,OOOOO,",  # d(3)
        ",OXXXXOO",  # e(4): je=O; ke..ne=X; oe,pe=O
        "OX.X..XO",  # f(5): if=O, jf=X, kf=., lf=X, mf,nf=., of=X, pf=O  (eye 1 at kf!)
        "OXX..XOO",  # g(6): ig=O; jg,kg=X; lg,mg=.; ng=X; og,pg=O
        "OO.X.XXO",  # h(7): ih,jh=O, kh=., lh=X, mh=., nh,oh=X, ph=O
        ",OXXXXOO",  # i(8): ji=O; ki..ni=X; oi,pi=O
        ",,OOOOO,",  # j(9)
    ], r0=3, c0=8, first="W", defender="B", cap_coords=["of"])

    # Also test a 7-9 move 1-2 Dan White-to-KILL via corner-skirt sacrifice (cols b..k, rows n..s — bottom-left skirt, W kills B!):
    # Flip and evolve our 7-move sacrifice-capture-connect idea with an EXTRA preliminary probe so it reaches **9 forced moves**!
    # How to add +2 forced moves to a 7-move sacrifice kill -> **9 FORCED MOVES**:
    # Before playing `nb` (which was Move 1 in P09), require White to play a 1st-line probe `1.W[probe] -> 2.B[block]` on the OTHER wing!
    # Why? Because without `1.W[probe]`, Black's main body has 1 extra eye-making point on the other wing!
    eval_dan("P10-9ply-masterpiece", [
        ",,OOOOOOOO,", # o(14): do..ko = O
        ",OOXXXXXOOO", # p(15): co,do? cp,dp=O; ep..ip=X; jp..lp=O
        "OOX..XXX.OO", # q(16): bq,cq=O; dq=X; eq,fq=.; gq..iq=X, jq=.; kq,lq=O
        "OX..XOO.XXO", # r(17): br=O, cr=X; dr,er=.; fr=X; gr,hr=O, ir=.; jr,kr=X, lr=O
        "O..X..X..XO", # s(18): bs=O; cs,ds=.; es=X; fs,gs=.; hs=X; is,js=.; ks=X, ls=O
    ], r0=14, c0=1, first="W", defender="B", cap_coords=["gr", "hr", "ir"])
