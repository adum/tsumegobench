#!/usr/bin/env python3
"""Find exact unique-solution 20-30k shapes for P01 (B live) and P02 (W kill)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fast_explore import eval_grid

if __name__ == "__main__":
    # P01 candidates (20-30k, Black to play and live, unique 1st move!)
    # 1) Top-right side: right wing has 1 eye at pa; left wing needs exact move to connect & form 2nd eye!
    eval_grid("P01-1", [
        ",OO..X.XO",  # a: ka=O, la=O, ma=., na=., oa=X, pa=., qa=X, ra=O
        "OXX.XXXXO",  # b: jb=O, kb=X, lb=X, mb=., nb=X, ob=X, pb=X, qb=X, rb=O
        ",OXXOOOOO",  # c: kc=O, lc=X, mc=X, nc=O, oc=O, pc=O, qc=O, rc=O
        ",,OO,,,,,",  # d: ld=O, md=O
    ], r0=0, c0=9, first="B", defender="B")

    #Wait: in P01-1, if ma=., na=., mb=.: if B plays ma, W plays mb (capturing kb-lb-lc-mc? kb-lb-lc-mc has libs ma and mb!).
    # Let's also check when kb-lb-lc has eye potential ONLY if ma is played OR mb is played!
    eval_grid("P01-2", [
        "OO..X.XO",   # a: ka=O, la=O, ma=., na=., oa=X, pa=., qa=X, ra=O
        "OX.XXXXO",   # b: kb=O, lb=X, mb=., nb=X, ob=X, pb=X, qb=X, rb=O
        "OXXXOOOO",   # c: kc=O, lc=X, mc=X, nc=X, oc=O, pc=O, qc=O, rc=O  <-- CONNECTED via nc!
        ",OOOO,,,",   # d: ld=O, md=O, nd=O, od=O
    ], r0=0, c0=10, first="B", defender="B")

    eval_grid("P01-3 (3-move B live, asymmetric top-side)", [
        "O..XX.XO",   # a: ka=O, la=., ma=., na=X, oa=X, pa=., qa=X, ra=O
        "OX.XXXXO",   # b: kb=O, lb=X, mb=., nb=X, ob=X, pb=X, qb=X, rb=O
        "OXXXOOOO",   # c: kc=O, lc=X, mc=X, nc=X, oc=O, pc=O, qc=O, rc=O
        ",OOOO,,,",   # d
    ], r0=0, c0=10, first="B", defender="B")

    # P02 candidates (20-30k, White to play and kill, unique 1st move, 3 moves!)
    # Look back at P02-v1: ONLY si AND sj killed! Why did BOTH si and sj kill in P02-v1?
    # Grid of P02-v1 was:
    #   ,,OO (g)
    #   ,OXX (h)
    #   OX.. (i: ri, si)
    #   OXX. (j: sj)
    #   ,OX. (k: sk)
    #   ,OXX (l)
    #   ,,OO (m)
    # Notice {ri, si, sj, sk} is a 4-space bent-four/T shape! If we make sk ALREADY an X stone, and put another half-eye above!
    eval_grid("P02-1 (right edge asymmetric W kill)", [
        ",,OO",  # g: rg=O, sg=O
        ",OXX",  # h: qh=O, rh=X, sh=X
        ",OX.",  # i: qi=O, ri=X, si=.   (top eye-pocket si if rj=X!)
        "OX..",  # j: pj=O, qj=X, rj=., sj=.
        "OXX.",  # k: pk=O, qk=X, rk=X, sk=.
        ",OXX",  # l: ql=O, rl=X, sl=X
        ",,OO",  # m: rm=O, sm=O
    ], r0=6, c0=15, first="W", defender="B")

    # Asymmetric stepped right-edge group so it's NOT any stock rectangle!
    eval_grid("P02-2 (right edge stepped W kill)", [
        ",,,OO",  # f: rf=O, sf=O
        ",,OX.",  # g: qg=O, rg=X, sg=.  <-- false-eye potential at sg if rh is cut or poked!
        ",OX.X",  # h: ph=O, qh=X, rh=., sh=X
        "OXX..",  # i: oi=O, pi=X, qi=X, ri=., si=.
        ",OXX.",  # j: pj=O, qj=X, rj=X, sj=.
        ",,OXX",  # k: qk=O, rk=X, sk=X
        ",,,OO",  # l: rl=O, sl=O
    ], r0=5, c0=14, first="W", defender="B")

    # Left-side asymmetric W kill with a cutting/peeping White stone!
    eval_grid("P02-3 (left edge W kill with peep)", [
        "OOO,,",  # f: af=O, bf=O, cf=O
        "XXO,,",  # g: ag=X, bg=X, cg=O
        ".XXO,",  # h: ah=., bh=X, ch=X, dh=O
        "..OX,",  # i: ai=., bi=., ci=O, di=X? No keep O connected!
    ][:3] + [
        "..OO,",  # i: ai=., bi=., ci=O, di=O
        ".XXO,",  # j: aj=., bj=X, cj=X, dj=O
        "X.XO,",  # k: ak=X, bk=., ck=X, dk=O
        "XXOO,",  # l: al=X, bl=X, cl=O, dl=O
        "OO,,,",  # m: am=O, bm=O
    ], r0=5, c0=0, first="W", defender="B")
