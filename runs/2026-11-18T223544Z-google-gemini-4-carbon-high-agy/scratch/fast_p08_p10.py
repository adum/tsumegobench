#!/usr/bin/env python3
"""Ultra-fast (<0.5s total) search for stepped, non-rectangular 7-9 move gems for P08 (1-4k W) and P10 (1-2d W)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_dan import eval_dan

if __name__ == "__main__":
    print("=== P08 CANDIDATES (1-4 kyu, White to play and LIVE, stepped non-rectangular shapes) ===")
    # 8A: Stepped right-side hook (cols n..s, rows h..p):
    # Top of White has 2-pt single eye {sh, si}? Put eye at {ro, so} at bottom (`qo=O, qp=O, rp=O, sp=O`? No, `{sp}` or `{ro, so}`!),
    # and on top (`h..m`) White must execute a 5-7 move throw-in / sacrifice / damezumari sequence to secure the 2nd eye!
    eval_dan("P08-stepped-A", [
        ",,,XXX",  # h(7): qh..sh = X
        ",,XX..",  # i(8): pi,qi=X; ri,si=.
        ",XXO.O",  # j(9): oj,pj=X; qj=O, rj=., sj=O
        "XXOOX.",  # k(10): nk,ok=X; pk,qk=O; rk=X, sk=.
        "XO.OO.",  # l(11): nl=X, ol=O, pl=., ql,rl=O, sl=.
        "XXOOO.",  # m(12): nm,om=X; pm..rm=O, sm=.  --> {sl, sm} is 2-pt single eye if sn=O? Wait make sn=X? No, if sn=X then sm touches X!
    ][:5] + [
        "XXOOOO",  # m(12): nm,om=X; pm..sm=O
        ",,XXO.",  # n(13): pn,qn=X; rn=O, sn=.   <-- {sn} is 1 real eye (rm,sm,rn=O)! Give 2-pt eye {rn,sn}?
    ][:5] + [
        "XXOOOO",  # m(12): nm,om=X; pm..sm=O
        ",,XX..",  # n(13): pn,qn=X; rn=., sn=.   <-- {rn,sn} surrounded by qn=X?! NO, qn=X destroys {rn}! Make qn=O!
    ][:5] + [
        "XOOOOO",  # m(12): nm=X; om..sm=O
        "XXXO..",  # n(13): nn..pn=X; qn=O; rn,sn=.  <-- {rn,sn} surrounded by qm,rm,sm,qn=O & bottom!
        ",,,OOO",  # o(14): qo,ro,so=O
        ",,,XXX",  # p(15): qp,rp,sp=X (connected to left wall via op,pp=X!)
    ], r0=7, c0=13, first="W", defender="W", cap_coords=["rk", "sj"], ignore_pts={"rn", "sn"})

    # Clean up 8A's bottom eye so outer Black is 1 connected wall:
    # Simply put White's 2-pt single eye at `{sh, si}` on TOP (`qh,rh=O, qg,rg,sg=X?` No, `{sh, si}` on 1st line surrounded by `rg=O, sg=O, rh=O, ri=O, rj=O, sj=O`!):
    eval_dan("P08-stepped-B", [
        ",,,XXX",  # f(5): qf..sf = X
        ",,XOOO",  # g(6): pg=X; qg,rg,sg=O
        ",,XO..",  # h(7): ph=X, qh=O; rh,sh=.   ({rh,sh}? qh,qg,rg,sg + qi,ri,si=O encloses {rh,sh}!)
        ",XXOOO",  # i(8): oi,pi=X; qi,ri,si=O
        "XXO..X",  # j(9): nj,oj=X; pj=O; qj,rj=.; sj=X
        "XOOX..",  # k(10): nk=X; ok,pk=O; qk=X; rk,sk=.
        ",XXO.O",  # l(11): ol,pl=X; ql=O, rl=., sl=O
        ",,XXXX",  # m(12): pm..sm = X
    ], r0=5, c0=13, first="W", defender="W", cap_coords=["qk", "ql", "sl"], ignore_pts={"rh", "sh"})

    # 8C: Stepped L-group where White lives by 5-7 move throw-in + connect-and-die!
    eval_dan("P08-stepped-C", [
        ",,,XXX",  # f(5): qf..sf = X
        ",,XOOO",  # g(6): pg=X; qg..sg=O
        ",,XO..",  # h(7): ph=X, qh=O; rh,sh=.  ({rh,sh} = 2-pt single eye!)
        ",XXOOO",  # i(8): oi,pi=X; qi..si=O
        "XXO...",  # j(9): nj,oj=X; pj=O; qj,rj,sj=.
        "XO.XX.",  # k(10): nk=X; ok=O, pk=.; qk,rk=X, sk=.
        "XOOOO.",  # l(11): nl=X; ol..rl=O, sl=.
        ",XXXXX",  # m(12): om..sm = X
    ], r0=5, c0=13, first="W", defender="W", cap_coords=["qk", "rk"], ignore_pts={"rh", "sh"})

    # 8D: Tweak 8C with `sj = O` (`sk = .`)!
    eval_dan("P08-stepped-D", [
        ",,,XXX",  # f(5)
        ",,XOOO",  # g(6)
        ",,XO..",  # h(7)
        ",XXOOO",  # i(8)
        "XXO..O",  # j(9): pj=O; qj,rj=.; sj=O
        "XO.XX.",  # k(10): ok=O, pk=.; qk,rk=X, sk=.
        "XOOOO.",  # l(11): ol..rl=O, sl=.
        ",XXXXX",  # m(12)
    ], r0=5, c0=13, first="W", defender="W", cap_coords=["qk", "rk"], ignore_pts={"rh", "sh"})

    print("\n=== P10 CANDIDATES (1-2 Dan, White to play and KILL or LIVE, 7-11 moves, non-rectangular!) ===")
    # 10A: Stepped center-skirt group (cols e..m, rows m..s) — White to KILL Black in 7-9 moves!
    # Look at an asymmetric T/boot Black group on the bottom edge (`f..l, n..s`), where Black has `{fs, gs}` 2-pt single eye on left,
    # and on right (`h..l, o..s`) White has 2 inside stones `iq=O, jq=O` (or `ir=O`) and executes a 7-9 move sacrifice + under-the-stones / squeeze!
    eval_dan("P10-dan-boot-A", [
        ",,,,OOOO,",  # m(12): im..lm = O
        ",,,OXXXOO",  # n(13): hn=O; in,jn,kn=X; ln,mn=O
        ",OOOX.XXO",  # o(14): fo..ho=O; io=X, jo=., ko,lo=X; mo=O
        "OXXXX..XO",  # p(15): ep=O; fp..ip=X; jp,kp=.; lp=X, mp=O
        "OXXXOO.OO",  # q(16): eq=O; fq..hq=X; iq,jq=O, kq=.; lq,mq=O
        "OX..XXOO,",  # r(17): er=O, fr=X; gr,hr=.; ir,jr=X; kr,lr=O  ({gr,hr}? Put eye at {fs,gs}!)
    ][:5] + [
        "OX..XOOO,",  # r(17): er=O, fr=X, gr,hr=., ir=X; jr..lr=O
        "OXXXXO,,,",  # s(18): es=O; fs..is=X; js=O
    ], r0=12, c0=4, first="W", defender="B", cap_coords=["iq", "jq"], ignore_pts={"gr", "hr"})

    # 10B: Clean 7-9 move 1-2 Dan White-to-KILL on left edge (cols a..e, rows f..o — tall asymmetric tower!):
    # Black has `{af, ag}` 2-pt eye on top, and below (`h..n`) White sacrifices + squeezes / plays under-the-stones!
    eval_dan("P10-dan-tower-B", [
        "OOOO,",  # e(4): ae..de = O
        ".XXO,",  # f(5): af=.; bf,cf=X; df=O
        ".XXO,",  # g(6): ag=.; bg,cg=X; dg=O   ({af,ag} = 2-pt single eye!)
        "XXXOO",  # h(7): ah..ch=X; dh,eh=O
        "..XXO",  # i(8): ai,bi=.; ci,di=X; ei=O
        "O.OXO",  # j(9): aj=O, bj=., cj=O, dj=X, ej=O
        ".OOXO",  # k(10): ak=., bk,ck=O, dk=X, ek=O? Wait bk,ck,cj=O is 3 stones! Make cj=X, bj=O!
    ][:5] + [
        ".OXXO",  # j(9): aj=., bj=O; cj,dj=X; ej=O
        "O.XXO",  # k(10): ak=O, bk=.; ck,dk=X; ek=O
        ".O.OO",  # l(11): al=., bl=O, cl=.; dl,el=O
        "..OO,",  # m(12): am,bm=.; cm,dm=O
        "OOO,,",  # n(13): an..cn = O
    ], r0=4, c0=0, first="W", defender="B", cap_coords=["bj", "ak", "bl"], ignore_pts={"af", "ag"})

    # 10C: Test 10B with `bl=X` (`dl=O`, `cm=O`) so Black encloses `{al, am}` unless White kills via `1.W[bi]`!
    eval_dan("P10-dan-tower-C", [
        "OOOO,",  # e(4)
        ".XXO,",  # f(5)
        ".XXO,",  # g(6)  ({af,ag} = 2-pt eye)
        "XXXOO",  # h(7): ah..ch=X; dh,eh=O
        "..O.O",  # i(8): ai,bi=., ci=O, di=., ei=O? Keep Black connected on col c!
    ][:4] + [
        ".OXXO",  # i(8): ai=., bi=O; ci,di=X; ei=O
        ".OXXO",  # j(9): aj=., bj=O; cj,dj=X; ej=O
        "..XOO",  # k(10): ak,bk=., ck=X; dk,ek=O
        "X.XOO",  # l(11): al=X, bl=., cl=X; dl,el=O
        ".XOO,",  # m(12): am=., bm=X; cm,dm=O
        ".OO,,",  # n(13): an=., bn,cn=O
        "OO,,,",  # o(14): ao,bo=O
    ], r0=4, c0=0, first="W", defender="B", cap_coords=["bi", "bj", "al", "bm"], ignore_pts={"af", "ag"})
