#!/usr/bin/env python3
"""
Construct and verify 1-4 kyu candidates (7-9 moves):
- problem-07: Black to play and KILL via true Under-the-Stones (ishi no shita) in bottom-right (cols l..s, rows o..s)
- problem-08: White to play and LIVE via Move-Order Probe + Damezumari in top-left (cols a..i, rows a..e)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, opp_color, play_move, sgf_to_pt


def analyze_deep(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, cap_coords: list[str]):
    b = w = ec = 0
    for dr, row_s in enumerate(grid):
        row = row_s.replace(" ", "")
        for dc, ch in enumerate(row):
            pt = (r0 + dr) * 19 + (c0 + dc)
            if ch == "X":
                b |= 1 << pt
            elif ch == "O":
                w |= 1 << pt
            elif ch == ".":
                ec |= 1 << pt
    def_stones = b if defender == "B" else w
    att_stones = w if defender == "B" else b
    cap = sum(1 << sgf_to_pt(s) for s in cap_coords)
    imm_att = att_stones & ~cap
    combat = ec | cap
    outside = BOARD_MASK ^ (ec | cap | def_stones)

    spec = TsumegoSpec(
        black=b, white=w, first_player=first, defender=defender,
        target_stones=def_stones, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=26)
    opp = opp_color(first)
    opp_v = sol.evaluate(b, w, opp)
    mvs = sol.analyze_moves(b, w, first)
    if not mvs:
        return
    bv = mvs[0][1]
    wins = [m for m, v in mvs if v == bv]
    print(f"=== {name} (stones={(b|w).bit_count()}, empty={ec.bit_count()}) ===")
    print(f"  Opp-first: {TsumegoSolver.OUTCOME_NAMES[opp_v]} | Best: {TsumegoSolver.OUTCOME_NAMES[bv]} | Wins: {wins}")
    print(f"  1st moves: {[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in mvs]}")

    if 1 <= len(wins) <= 2 and opp_v != bv:
        def trace(cb, cw, ck, side, d, path):
            if d > 11:
                return
            cmvs = sol.analyze_moves(cb, cw, side, ck)
            if side == first:
                cwins = [m for m, v in cmvs if v == bv]
                print("  " * d + f"{path} -> {first} wins: {cwins}")
                for m in cwins[:2]:
                    nb, nw, nk = play_move(cb, cw, side, sgf_to_pt(m), ck)
                    threats = []
                    for am, av in sol.analyze_moves(nb, nw, opp, nk):
                        nb2, nw2, nk2 = play_move(nb, nw, opp, sgf_to_pt(am), nk)
                        if sol.evaluate(nb2, nw2, opp, None) != bv:
                            threats.append((am, nb2, nw2, nk2))
                    if not threats:
                        print("  " * (d + 1) + f"{first}[{m}] SETTLES at ply {d+1}!")
                    else:
                        for am, nb2, nw2, nk2 in threats[:3]:
                            trace(nb2, nw2, nk2, first, d + 2, f"{first}[{m}]->{opp}[{am}]")
        for m1 in wins:
            nb, nw, nk = play_move(b, w, first, sgf_to_pt(m1))
            for am, _ in sol.analyze_moves(nb, nw, opp, nk):
                nb2, nw2, nk2 = play_move(nb, nw, opp, sgf_to_pt(am), nk)
                if sol.evaluate(nb2, nw2, opp, None) != bv:
                    trace(nb2, nw2, nk2, first, 2, f"1.{first}[{m1}]->2.{opp}[{am}]")


if __name__ == "__main__":
    # === P07: True Under-the-Stones (ishi no shita) in bottom-right (cols l..s, rows o..s) ===
    # How ishi no shita works cleanly:
    # White has 1 real eye at {ss} (`rs=O, rr=O, sr=O` -> `{ss}` is 1 eye!).
    # On the left of White's group (`l..q`):
    # Black's outer wall is `lo, mo, no, oo, po, qo, ro, so` + `lp, lq, lr, ls`!
    # White's left wall inside is `mp=O`? No: `mq=O` (isolated from `op, pp, qp, rp`? YES!!):
    # LOOK AT `mq = O` (`lp=X, mp=X, lq=X, lr=X, ls=X`!):
    # `mq = O` ONLY connects to White's right body via `mr, ms` or `nq`!
    # Put Black sacrifice stones at `nr = X, or = X`, surrounded on top by `nq=O, oq=O, pq=O`!
    # Trace!!
    #   o(14): X X X X X X X X   (lo..so = X)
    #   p(15): X X X O O O O O   (lp,mp,np=X; op,pp,qp,rp,sp=O? Wait keep sp=X? No, corner {ss} is W!)
    #   q(16): X O O O O X O O   (lq=X; mq,nq,oq,pq=O; qq=X? No, keep W connected on top: nq,oq,pq,qq=O, and mq=O!)
    #   Wait: for 5.B[nr] (under the stones!) to put W's capturing stones in ATARI:
    #   The White stones that capture Black's 3-stone sacrifice `{nr, or, os}` MUST be cut off from White's main body!
    #   Look: put `mq = X` (Black outer wall!), `mr = O` (White's isolated left jaw stone, liberties `ms` and `nr`? No, if `nr=X`, `mr=O` only has 1 lib `ms`!).
    #   Give `mr=O, mq=O` (`lp=X, mp=X, np=X`, `lq=X, lr=X, ls=X`): `mq-mr` has liberties `nq`? If `nq=X` (outer wall!), then `mq-mr` is cut off on top!
    #   YES!! LOOK AT `nq = X` (part of Black's outer wall!!):
    #     o(14): , X X X X X X X   (mo..so = X)
    #     p(15): X X X O O O O O   (lp,mp,np = X; op,pp,qp,rp,sp = O)
    #     q(16): X O X X O O O O   (lq=X, mq=O, nq=X, oq=X, pq=O, qq=O, rq=O, sq=O) -> wait `nq=X, oq=X` pokes in!
    #     r(17): X O . X X O O O   (lr=X, mr=O, nr=., or=X, pr=X, qr=O, rr=O, sr=O)
    #     s(18): X . . . . O . O   (ls=X, ms=., ns=., os=., ps=., qs=O, rs=., ss=O? rs=. is eye #1!)
    #   TRACE `mq-mr` AND `or-pr` IN THAT DIAGRAM!!
    #   - `mq-mr` (2 White stones on left!) has ONLY liberties `nr` and `ms`!
    #   - `or-pr` (2 Black stones inside!) is connected to `oq=X`!! Wait: if `or` is connected to `oq=X`, it's NOT a sacrifice — make `oq = O` so `or-pr` is ISOLATED inside White (`oq=O, pq=O, qr=O`)!!
    #   TEST BOTH `oq=O` AND VARIANTS RIGHT NOW!
    analyze_deep("P07-ishi-A", [
        ",XXXXXXX",  # o(14): mo..so = X
        "XXXOOOOX",  # p(15): lp,mp,np=X; op..rp=O; sp=X
        "XOXOOOOX",  # q(16): lq=X, mq=O, nq=X, oq..rq=O, sq=X
        "XO.XXOOO",  # r(17): lr=X, mr=O, nr=., or=X, pr=X, qr=O, rr=O, sr=O
        "X....O.O",  # s(18): ls=X, ms=., ns=., os=., ps=., qs=O, rs=., ss=O
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mq", "mr", "or", "pr"])

    analyze_deep("P07-ishi-B", [
        ",XXXXXXX",  # o(14)
        "XXXOOOOX",  # p(15)
        "XOXOOOOX",  # q(16): lq=X, mq=O, nq=X, oq..rq=O, sq=X
        "XO..XOOO",  # r(17): lr=X, mr=O, nr=., or=., pr=X, qr=O, rr=O, sr=O
        "X...XO.O",  # s(18): ls=X, ms=., ns=., os=., ps=X, qs=O, rs=., ss=O
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mq", "mr", "pr", "ps"])

    analyze_deep("P07-ishi-C", [
        ",,XXXXXX",  # o(14): no..so = X
        ",XXOOOOX",  # p(15): mp,np=X; op..rp=O; sp=X
        "XXOOOOOX",  # q(16): lq,mq=X; nq..rq=O; sq=X
        "XO..XXOO",  # r(17): lr=X, mr=O, nr=., or=., pr=X, qr=X, rr=O, sr=O? Wait qr=X cuts! Make pr=X, qr=O!
    ][:3] + [
        "XO..XOOO",  # r(17): lr=X, mr=O, nr=., or=., pr=X, qr=O, rr=O, sr=O
        "X....O.O",  # s(18): ls=X, ms=., ns=., os=., ps=., qs=O, rs=., ss=O
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mr", "pr"])

    # === P08: White to play and LIVE in top-left (cols a..i, rows a..e) via Probe + 1st-line Tesuji (7-9 moves) ===
    analyze_deep("P08-probe-live-A", [
        ".OO..O.X,",  # a(0): aa=., ba=O, ca=O, da=., ea=., fa=O, ga=., ha=X
        "OO.OO.XX,",  # b(1): ab=O, bb=O, cb=., db=O, eb=O, fb=., gb=X, hb=X
        "XXOOXXXX,",  # c(2): ac=X, bc=X, cc=O, dc=O, ec=X, fc=X, gc=X, hc=X
        ",,XXXX,,,",  # d(3): cd..fd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["fa", "ac", "bc"])

    analyze_deep("P08-probe-live-B", [
        "..O..OXX,",  # a(0): aa=., ba=., ca=O, da=., ea=., fa=O, ga=X, ha=X
        "XO.OO.XX,",  # b(1): ab=X, bb=O, cb=., db=O, eb=O, fb=., gb=X, hb=X
        "XXOOXXXX,",  # c(2): ac=X, bc=X, cc=O, dc=O, ec=X, fc=X, gc=X, hc=X
        ",,XXXX,,,",  # d(3)
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["fa", "ab", "ac", "bc"])
