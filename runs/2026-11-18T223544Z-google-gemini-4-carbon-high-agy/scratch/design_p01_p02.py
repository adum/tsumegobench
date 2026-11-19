#!/usr/bin/env python3
"""Explore and verify candidate shapes for problem-01 (20-30k B live) and problem-02 (20-30k W kill)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, pt_to_sgf, sgf_to_pt


def parse_ascii_setup(lines: list[str], row_start: int, col_start: int):
    """
    Parse ASCII grid where:
      'X' = Black, 'O' = White, '.' = empty inside combat_mask, ',' = empty outside combat_mask
    """
    black = 0
    white = 0
    combat = 0
    for dr, line in enumerate(lines):
        row = line.replace(" ", "")
        for dc, ch in enumerate(row):
            r = row_start + dr
            c = col_start + dc
            pt = r * 19 + c
            if ch == "X":
                black |= 1 << pt
                combat |= 1 << pt
            elif ch == "O":
                white |= 1 << pt
            elif ch == ".":
                combat |= 1 << pt
            elif ch == ",":
                pass
            else:
                raise ValueError(f"Unknown char {ch!r}")
    return black, white, combat


def test_shape(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, weak_att_coords: list[str] = ()):
    b, w, combat = parse_ascii_setup(grid, r0, c0)
    def_stones = b if defender == "B" else w
    att_stones = w if defender == "B" else b
    weak_att = sum(1 << sgf_to_pt(s) for s in weak_att_coords)
    combat |= weak_att
    imm_att = att_stones & ~weak_att
    outside = BOARD_MASK ^ combat

    spec = TsumegoSpec(
        black=b,
        white=w,
        first_player=first,
        defender=defender,
        target_stones=def_stones,
        combat_mask=combat,
        outside_mask=outside,
        immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=20)
    mvs = sol.analyze_moves(b, w, first)
    opp = "W" if first == "B" else "B"
    opp_val = sol.evaluate(b, w, opp)
    print(f"=== {name} (stones={(b|w).bit_count()}, empty={(combat & ~(b|w)).bit_count()}) ===")
    print(f"  If {opp} moved first: {TsumegoSolver.OUTCOME_NAMES[opp_val]}")
    print("  1st moves:", [(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in mvs])
    if mvs:
        best_m, best_v = mvs[0]
        nb, nw, nko = play_move(b, w, first, sgf_to_pt(best_m))
        resp = sol.analyze_moves(nb, nw, opp, nko)
        print(f"  After {first}[{best_m}], {opp} replies:", [(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in resp])
        for rm, rv in resp[:4]:
            nb2, nw2, nko2 = play_move(nb, nw, opp, sgf_to_pt(rm), nko)
            r3 = sol.analyze_moves(nb2, nw2, first, nko2)
            wins3 = [m3 for m3, v3 in r3 if v3 == best_v]
            print(f"    If {opp}[{rm}] -> {first} winning replies: {wins3} (all: {[(m3, TsumegoSolver.OUTCOME_NAMES[v3]) for m3,v3 in r3[:4]]})")


if __name__ == "__main__":
    # Candidate 1A for problem-01 (25-28k): Black to live on top edge (cols f..n, rows a..d)
    # Left wing has 1 eye at ha; right wing has endangered stone la/lb or cut + capture!
    # Wait: suppose White has an inside stone at kb in 2 liberties (ka, lb) and ma is White outside:
    # Let's test!
    test_shape(
        "P01-candA (top edge f..n, a..d)",
        [
            "OX.X..XO,",  # a: fa=O, ga=X, ha=., ia=X, ja=., ka=., la=X, ma=O, na=,
            "OXXX.OXO,",  # b: fb=O, gb=X, hb=X, ib=X, jb=., kb=O, lb=X, mb=O
            ",OOOXXXO,",  # c: gc=O, hc=O, ic=O, jc=X, kc=X, lc=X, mc=O
            ",,,OOOO,,",  # d: id=O, jd=O, kd=O, ld=O
        ],
        r0=0, c0=5, first="B", defender="B", weak_att_coords=["kb"]
    )

    # Candidate 1B: Black to live in 3 moves (atari/connect/eye split) on top edge
    test_shape(
        "P01-candB (top edge f..n, a..d)",
        [
            "OX.X...O,",  # a: fa=O, ga=X, ha=., ia=X, ja=., ka=., la=., ma=O
            "OXXX.OXXO",  # b: fb=O, gb=X, hb=X, ib=X, jb=., kb=O, lb=X, mb=X, nb=O
            ",OOOX.XO,",  # c: gc=O, hc=O, ic=O, jc=X, kc=., lc=X, mc=O
            ",,,OOOO,,",  # d: id=O, jd=O, kd=O, ld=O
        ],
        r0=0, c0=5, first="B", defender="B", weak_att_coords=["kb"]
    )

    # Candidate 2A for problem-02 (21-24k): White to kill on left edge (cols a..d, rows g..n)
    # Black has an asymmetric group with a 3-space/tiger shape where W plays vital point -> 2 branches -> dead!
    test_shape(
        "P02-candA (left edge a..d, g..n)",
        [
            "OO,,",  # g: ag=O, bg=O
            "XXO,",  # h: ah=X, bh=X, ch=O
            "..XO",  # i: ai=., bi=., ci=X, di=O
            ".XXO",  # j: aj=., bj=X, cj=X, dj=O
            ".XO,",  # k: ak=., bk=X, ck=O
            "XXO,",  # l: al=X, bl=X, cl=O
            "OO,,",  # m: am=O, bm=O
        ],
        r0=6, c0=0, first="W", defender="B"
    )

    # Candidate 2B for problem-02 (21-24k): White to kill on left edge with cutting/false-eye stone
    test_shape(
        "P02-candB (left edge a..d, g..n)",
        [
            "OOO,",  # g
            "X.XO",  # h: ah=X, bh=., ch=X, dh=O  (top half-eye / tiger mouth!)
            ".XXO",  # i: ai=., bi=X, ci=X, di=O
            ".O.,",  # j: aj=., bj=O, cj=.,
            "XXXO",  # k: ak=X, bk=X, ck=X, dk=O
            ".XOO",  # l: al=., bl=X, cl=O, dl=O (1 false/potential eye at al? Wait: al surrounded by ak,bl,am=O!)
            "OO,,",  # m: am=O, bm=O
        ],
        r0=6, c0=0, first="W", defender="B", weak_att_coords=["bj"]
    )
