#!/usr/bin/env python3
"""
Inspect the stepped right-side Seki candidate for problem-08 (1-4 kyu, W to live in seki)
and search tall L-shaped / stepped 7-11 move 1-2 dan candidates for problem-10 (W to play).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, opp_color, play_move, sgf_to_pt
from search_dan import eval_dan


def trace_seki_tree():
    print("=== Inspecting Stepped Right-Side Seki Candidate for P08 (1-4 kyu) ===")
    g = [
        ",,XXXX",  # g(6): pg..sg = X
        ",XXO..",  # h(7): oh,ph=X; qh=O; rh,sh=.
        "XXOO..",  # i(8): ni,oi=X; pi,qi=O; ri,si=.
        "XO.XXO",  # j(9): nj=X; oj=O, pj=.; qj,rj=X, sj=O
        "XOO.O.",  # k(10): nk=X; ok,pk=O, qk=., rk=O, sk=.
        ",XXOO.",  # l(11): ol,pl=X; ql,rl=O, sl=.
        ",,XXXX",  # m(12): pm..sm = X
    ]
    b = w = ec = 0
    for dr, r in enumerate(g):
        for dc, ch in enumerate(r):
            pt = (6 + dr) * 19 + (13 + dc)
            if ch == "X": b |= 1 << pt
            elif ch == "O": w |= 1 << pt
            elif ch == ".": ec |= 1 << pt
    # Include qh, pi, qi, sj, rk, ql, rl, qj, rj in cap? Check small chains!
    cap = sum(1 << sgf_to_pt(s) for s in ["qj", "rj", "sj", "rk", "ql", "rl"])
    sp = TsumegoSpec(black=b, white=w, first_player="W", defender="W", target_stones=w,
                     combat_mask=ec | cap, outside_mask=BOARD_MASK ^ (ec | cap | w),
                     immortal_attacker=b & ~sum(1 << sgf_to_pt(s) for s in ["qj", "rj"]))
    sol = TsumegoSolver(sp, max_depth=26)
    print("Opp-first:", TsumegoSolver.OUTCOME_NAMES[sol.evaluate(b, w, "B")])
    print("1st moves:", [(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in sol.analyze_moves(b, w, "W")])
    b1, w1, k1 = play_move(b, w, "W", sgf_to_pt("rh"))
    for m2, v2 in sol.analyze_moves(b1, w1, "B", k1):
        b2, w2, k2 = play_move(b1, w1, "B", sgf_to_pt(m2), k1)
        w3 = [m for m, v in sol.analyze_moves(b2, w2, "W", k2) if v == 2]
        print(f"  1.W[rh] -> 2.B[{m2}] ({TsumegoSolver.OUTCOME_NAMES[v2]}) -> 3.W seki moves: {w3}")
        for m3 in w3[:3]:
            b3, w3b, k3 = play_move(b2, w2, "W", sgf_to_pt(m3), k2)
            for m4, _ in sol.analyze_moves(b3, w3b, "B", k3):
                b4, w4, k4 = play_move(b3, w3b, "B", sgf_to_pt(m4), k3)
                if sol.evaluate(b4, w4, "B", None) < 2:
                    w5 = [m for m, v in sol.analyze_moves(b4, w4, "W", k4) if v == 2]
                    print(f"     3.W[{m3}] -> 4.B[{m4}] (real threat!) -> 5.W seki moves: {w5}")
                    for m5 in w5[:2]:
                        b5, w5b, k5 = play_move(b4, w4, "W", sgf_to_pt(m5), k4)
                        for m6, _ in sol.analyze_moves(b5, w5b, "B", k5):
                            b6, w6, k6 = play_move(b5, w5b, "B", sgf_to_pt(m6), k5)
                            if sol.evaluate(b6, w6, "B", None) < 2:
                                w7 = [m for m, v in sol.analyze_moves(b6, w6, "W", k6) if v == 2]
                                print(f"        5.W[{m5}] -> 6.B[{m6}] (real threat!) -> 7.W seki moves: {w7}")


if __name__ == "__main__":
    trace_seki_tree()

    print("\n=== Testing Stepped L-Shaped 7-9 Move 1-2 Dan Candidates for P10 (White to play) ===")
    # Candidate 10A: Tall stepped L-shape on left-top / center-left (cols a..f, rows h..p), White to KILL in 7-9 moves!
    # Look! White surrounds a stepped Black L-group on the left side (`a..e, i..p`):
    # Upper arm of Black has a 2-pt single eye `{ai, aj}`, lower arm has a sacrificial White stone inside (`cm=O, cn=O`),
    # where White plays a 7-move sacrifice/connect/squeeze kill (like P09 in a totally different stepped vertical L-shape + extra probe!)
    eval_dan("P10-stepped-kill-A", [
        "OOO,,",  # h(7): ah,bh,ch = O
        "..OO,",  # i(8): ai,bi=.; ci,di=O  -> wait Black needs stones around {ai, aj}!
    ][:0] + [
        "OOOO,,", # h(7): ah..dh = O
        ".XXOO,", # i(8): ai=., bi,ci=X; di,ei=O
        ".XXOO,", # j(9): aj=., bj,cj=X; dj,ej=O   ({ai,aj} is Black's 2-pt single eye!)
        "XX.XOO", # k(10): ak,bk=X, ck=., dk=X; ek,fk=O
        "XOOXOO", # l(11): al=X; bl,cl=O; dl=X; el,fl=O
        ".X.XO,", # m(12): am=., bm=X, cm=., dm=X, em=O
        ".X..O,", # n(13): an=., bn=X, cn=., dn=., en=O
        "O..OO,", # o(14): ao=O, bo=., co=., do=O, eo=O? Keep O connected:
    ][:7] + [
        "OO.OO,", # o(14): ao,bo=O, co=., do,eo=O
        ",,O,,,", # p(15): cp=O
    ], r0=7, c0=0, first="W", defender="B", cap_coords=["bl", "cl", "bm", "bn", "dk", "dl", "dm"], ignore_pts={"ai", "aj"})

    # Candidate 10B: Stepped corner+wing L-shape (bottom-left climbing up, cols a..f, rows k..s), White to LIVE in 7 moves!
    # White has a tall group on left edge (`a..d, l..s`) with 1 eye `{as, bs}` at bottom,
    # and on top (`l..p`) must execute a 7-move probe + throw-in + eye-maker to get the 2nd eye!
    eval_dan("P10-tall-live-B", [
        "XXXX,",  # k(10): ak..dk = X
        "..XX,",  # l(11): al,bl=.; cl,dl=X
        ".O.XX",  # m(12): am=., bm=O, cm=.; dm,em=X
        "X.OOX",  # n(13): an=X, bn=., cn,dn=O, en=X
        "XXO.X",  # o(14): ao,bo=X, co=O, do=., eo=X
        "XOOOX",  # p(15): ap=X; bp,cp,dp=O; ep=X
        "OOXXX",  # q(16): aq,bq=O; cq,dq,eq=X
        ".OOX,",  # r(17): ar=.; br,cr=O; dr=X
        ".OOX,",  # s(18): as=.; bs,cs=O; ds=X   ({ar,as} = 2-pt single eye!)
    ], r0=10, c0=0, first="W", defender="W", cap_coords=["bm", "an", "ao", "bo"], ignore_pts={"ar", "as"})

    # Candidate 10C: Tweak P10-tall-live-B where `an, ao` are Black inside stones cut off from Black's outer wall!
    # Look! In 10B, `an, ao, bo` was on the 1st line (`a`), so it WAS cut off from `ak..dk` and `aq=O` below!!
    # Let's also test `ao=X, bo=X` (2 Black inside stones!) with `an=.`:
    eval_dan("P10-tall-live-C", [
        "XXXX,",  # k(10): ak..dk = X
        "..XX,",  # l(11): al,bl=.; cl,dl=X
        "O..XX",  # m(12): am=O, bm,cm=.; dm,em=X
        ".XOOX",  # n(13): an=., bn=X; cn,dn=O; en=X
        "XXOOX",  # o(14): ao,bo=X; co,do=O; eo=X
        ".OOXX",  # p(15): ap=.; bp,cp=O; dq,eq? dp,ep=X
        "OOOXX",  # q(16): aq,bq,cq=O; dq,eq=X
        ".OOX,",  # r(17): ar=.; br,cr=O; dr=X
        ".OOX,",  # s(18): as=.; bs,cs=O; ds=X
    ], r0=10, c0=0, first="W", defender="W", cap_coords=["am", "bn", "ao", "bo"], ignore_pts={"ar", "as"})
