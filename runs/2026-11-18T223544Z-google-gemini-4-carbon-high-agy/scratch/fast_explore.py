#!/usr/bin/env python3
"""Ultra-fast (<0.1s) shape explorer — includes small/vulnerable chains in combat_mask cleanly."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, dilate, iter_components, play_move, sgf_to_pt


def eval_grid(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, capturable_coords: list[str] = ()):
    t0 = time.time()
    b = w = empty_combat = 0
    for dr, row_s in enumerate(grid):
        row = row_s.replace(" ", "")
        for dc, ch in enumerate(row):
            pt = (r0 + dr) * 19 + (c0 + dc)
            if ch == "X":
                b |= 1 << pt
            elif ch == "O":
                w |= 1 << pt
            elif ch == ".":
                empty_combat |= 1 << pt
            elif ch == ",":
                pass
    cap_mask = sum(1 << sgf_to_pt(s) for s in capturable_coords)
    def_stones = b if defender == "B" else w
    att_stones = w if defender == "B" else b
    # Also include any small (<= 3 stones) defender chain in cap_mask in case it gets captured & re-played (ko/snapback)
    for ch in iter_components(def_stones):
        if ch.bit_count() <= 4:
            cap_mask |= ch
    imm_att = att_stones & ~cap_mask
    combat = empty_combat | cap_mask
    outside = BOARD_MASK ^ (empty_combat | def_stones | cap_mask)

    spec = TsumegoSpec(
        black=b, white=w, first_player=first, defender=defender,
        target_stones=def_stones, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=20)
    opp = "W" if first == "B" else "B"
    opp_v = sol.evaluate(b, w, opp)
    mvs = sol.analyze_moves(b, w, first)
    dt = (time.time() - t0) * 1000
    print(f"=== {name} [{dt:.1f}ms, stones={(b|w).bit_count()}, empty={empty_combat.bit_count()}] ===")
    print(f"  Opp-first: {TsumegoSolver.OUTCOME_NAMES[opp_v]} | 1st moves: {[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in mvs]}")
    if mvs:
        bm, bv = mvs[0]
        nb, nw, nko = play_move(b, w, first, sgf_to_pt(bm))
        r2 = sol.analyze_moves(nb, nw, opp, nko)
        print(f"  After {first}[{bm}] -> {opp}: {[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in r2]}")
        for m2, _ in r2[:5]:
            nb2, nw2, nko2 = play_move(nb, nw, opp, sgf_to_pt(m2), nko)
            r3 = [m3 for m3, v3 in sol.analyze_moves(nb2, nw2, first, nko2) if v3 == bv]
            print(f"    {opp}[{m2}] -> {first} wins: {r3}")
    return spec, sol
