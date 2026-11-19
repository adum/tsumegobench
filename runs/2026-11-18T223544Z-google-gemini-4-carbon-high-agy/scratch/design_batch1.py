#!/usr/bin/env python3
"""Design unique-key-move, original 20-30k shapes for P01 (B live) and P02 (W kill)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fast_explore import eval_grid

if __name__ == "__main__":
    # --- P01 (20-30k, Black to play and live) ---
    # Idea 1: Top edge (cols f..n, rows a..d).
    # Left wing has 1 real eye at ha (ga,gb,hb,ia,ib).
    # Right wing has jc,kc,lc,lb, with White at ma,mb,mc... and White stone at kb?
    # Wait: if la is empty, ja is empty, jb is empty, ka is empty, and kb=O:
    eval_grid("P01-A (save eye against O[kb])", [
        "OX.X...O,",  # a: fa=O, ga=X, ha=., ia=X, ja=., ka=., la=., ma=O
        "OXXX.OXO,",  # b: fb=O, gb=X, hb=X, ib=X, jb=., kb=O, lb=X, mb=O
        ",OOOXXXO,",  # c: gc=O, hc=O, ic=O, jc=X, kc=X, lc=X, mc=O
        ",,,OOOO,,",  # d: id=O, jd=O, kd=O, ld=O
    ], r0=0, c0=5, first="B", defender="B", capturable_coords=["kb"])

    # Idea 2: What if ic=X too so jc-kc-lc is already connected to ib, and lb=O (so kb-lb is connected to outer wall? No, if kb is connected to outer wall it can't be captured!).
    # What if NO White stone inside yet, instead Black has an asymmetric L-hook with an outside White peep!
    eval_grid("P01-B (connect & split on top edge)", [
        "OX.X..XO,",  # a: fa=O, ga=X, ha=., ia=X, ja=., ka=., la=X, ma=O
        "OXX..XXO,",  # b: fb=O, gb=X, hb=X, ib=., jb=., kb=X, lb=X, mb=O
        ",OOXXXOO,",  # c: gc=O, hc=O, ic=X, jc=X, kc=X, lc=O, mc=O
        ",,OOOO,,,",  # d: hd=O, id=O, jd=O, kd=O
    ], r0=0, c0=5, first="B", defender="B")

    # Idea 3: Asymmetric stepped group near top-right side (cols k..r, rows a..e)
    # Black has eye at pa (oa,ob,pb,qa,qb), and on left wing needs 1 key move at mb/mc!
    eval_grid("P01-C (stepped top-side B live)", [
        ",O..X.XO",  # a: la=O, ma=., na=., oa=X, pa=., qa=X, ra=O
        "OX.XXXXO",  # b: kb=O, lb=X, mb=., nb=X, ob=X, pb=X, qb=X, rb=O
        "OXXOOOOO",  # c: kc=O, lc=X, mc=X, nc=O, oc=O, pc=O, qc=O, rc=O
        ",OOO,,,,",  # d: ld=O, md=O, nd=O
    ], r0=0, c0=10, first="B", defender="B")

    # Idea 4: Stepped side group on left edge (cols a..e, rows f..n)
    eval_grid("P01-D (left edge stepped B live)", [
        "OOO,,",  # f: af=O, bf=O, cf=O
        "X.XO,",  # g: ag=X, bg=., cg=X, dg=O
        "X.XXO",  # h: ah=X, bh=., ch=X, dh=X, eh=O
        ".O.XO",  # i: ai=., bi=O, ci=., di=X, ei=O
        "XXOXO",  # j: aj=X, bj=X, cj=O, dj=X, ej=O? Wait cj=O cuts! Make cj=X!
    ][:4] + [
        "XXXXO",  # j: aj=X, bj=X, cj=X, dj=X, ej=O
        "OOOO,",  # k: ak=O, bk=O, ck=O, dk=O
    ], r0=5, c0=0, first="B", defender="B", capturable_coords=["bi"])

    # --- P02 (20-30k, White to play and kill) ---
    # Look at P02-v1 earlier: only si and sj killed! Let's make ONLY ONE move kill!
    # Why did both si and sj kill in P02-v1? Because ri,si,sj,sk was a 4-space T/bent shape?
    # Let's tweak P02-v1 so ONLY ONE first move kills unconditionally!
    eval_grid("P02-A (right edge W kill, unique vital point)", [
        ",,OO",  # g: rg=O, sg=O
        ",OXX",  # h: qh=O, rh=X, sh=X
        "OX..",  # i: pi=O, qi=X, ri=., si=.
        "OX.X",  # j: pj=O, qj=X, rj=., sj=X
        "OXX.",  # k: pk=O, qk=X, rk=X, sk=.
        ",OXX",  # l: ql=O, rl=X, sl=X
        ",,OO",  # m: rm=O, sm=O
    ], r0=6, c0=15, first="W", defender="B")

    eval_grid("P02-B (bottom-left side W kill, unique vital point)", [
        ",OOOO,,,",  # o: co=O, do=O, eo=O, fo=O
        "OXXXXOO,",  # p: bp=O, cp=X, dp=X, ep=X, fp=X, gp=O, hp=O
        "OX..XXO,",  # q: bq=O, cq=X, dq=., eq=., fq=X, gq=X, hq=O
        "OXX..XO,",  # r: br=O, cr=X, dr=X, er=., fr=., gr=X, hr=O
        ",,OOXOO,",  # s: ds=O, es=O, fs=X, gs=O, hs=O? Wait fs=X has 1 lib fr!
    ], r0=14, c0=1, first="W", defender="B")

    eval_grid("P02-C (enclosed 2nd-line box + edge, W kill)", [
        ",,OOOO,,",  # o
        ",OXXXXO,",  # p: cp=O, dp=X, ep=X, fp=X, gp=X, hp=O
        "OXX..XXO",  # q: bq=O, cq=X, dq=X, eq=., fq=., gq=X, hq=X, iq=O
        "OX.XX.XO",  # r: br=O, cr=X, dr=., er=X, fr=X, gr=., hr=X, ir=O
        "OO.OO.OO",  # s: bs=O, cs=O, ds=., es=O, fs=O, gs=., hs=O, is=O
    ], r0=14, c0=1, first="W", defender="B")
