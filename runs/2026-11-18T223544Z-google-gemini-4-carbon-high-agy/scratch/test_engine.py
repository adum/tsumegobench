#!/usr/bin/env python3
"""Fast verification test of TsumegoSolver on canonical reference SGFs."""

import time
from pathlib import Path
from go_engine import (
    BOARD_MASK, TsumegoSolver, TsumegoSpec, dilate, flood_fill,
    iter_components, parse_sgf_strict, sgf_to_pt,
)

ROOT = Path(__file__).resolve().parent.parent


def make_spec_from_target(sgf_text: str, defender: str, target_seed_coord: str) -> TsumegoSpec:
    root, errs = parse_sgf_strict(sgf_text)
    assert not errs, errs
    black = 0
    white = 0
    for s in root.props.get("AB", []):
        black |= 1 << sgf_to_pt(s)
    for s in root.props.get("AW", []):
        white |= 1 << sgf_to_pt(s)
    for s in root.props.get("AE", []):
        p = sgf_to_pt(s)
        black &= ~(1 << p)
        white &= ~(1 << p)

    first_col = "B" if "B" in root.children[0].props else "W"
    def_stones = black if defender == "B" else white
    att_stones = white if defender == "B" else black

    seed_bit = 1 << sgf_to_pt(target_seed_coord)
    # Identify outer attacker wall: attacker chains with >= 4 liberties, or specified wall
    empty = BOARD_MASK ^ (black | white)
    immortal_att = 0
    for ch in iter_components(att_stones):
        if (dilate(ch) & empty).bit_count() >= 4:
            immortal_att |= ch

    # Flood fill enclosed area from seed_bit through ~(immortal_att)
    enclosure = flood_fill(seed_bit, BOARD_MASK ^ immortal_att)
    target = enclosure & def_stones
    combat = enclosure & ~(immortal_att)
    # Include liberties of any weak (<=3 lib) attacker chain touching enclosure
    for ch in iter_components(att_stones & ~immortal_att):
        if dilate(ch) & enclosure:
            combat |= (dilate(ch) & empty)
    outside = BOARD_MASK ^ (enclosure | immortal_att)

    return TsumegoSpec(
        black=black,
        white=white,
        first_player=first_col,
        defender=defender,
        target_stones=target,
        combat_mask=combat,
        outside_mask=outside,
        immortal_attacker=immortal_att,
    )


def main():
    cases = [
        ("gp-18843.sgf", "B", "ab", "26k B to live (expect ba:CLEAN_LIFE)"),
        ("gp-5973.sgf",  "W", "br", "21k B to get seki vs W (expect cr,dr:SEKI)"),
        ("gp-39693.sgf", "W", "md", "18k B to kill W via snapback (expect nd:DEAD)"),
        ("gp-10507.sgf", "W", "mb", "13k W to live (expect qb:CLEAN_LIFE, qa/pb:KO)"),
        ("gp-16482.sgf", "B", "ar", "8k W to kill B (expect cs,dq:DEAD)"),
        ("gp-36582.sgf", "B", "qc", "4k W to kill B by ko (expect rc:KO)"),
        ("gp-20284.sgf", "B", "dr", "1d W to kill B (expect gr:DEAD)"),
        ("gp-38368.sgf", "B", "nd", "1d W to kill B (expect oe:DEAD)"),
    ]
    for fname, def_col, seed, desc in cases:
        t0 = time.time()
        sgf_text = (ROOT / "inputs/examples" / fname).read_text()
        spec = make_spec_from_target(sgf_text, def_col, seed)
        solver = TsumegoSolver(spec, max_depth=26)
        moves = solver.analyze_moves(spec.black, spec.white, spec.first_player)
        dt = (time.time() - t0) * 1000
        top_str = ", ".join(f"{m}:{TsumegoSolver.OUTCOME_NAMES[v]}" for m, v in moves[:6])
        print(f"{fname:13s} [{dt:6.1f} ms, {solver.nodes_searched:6d} nodes] {desc}")
        print(f"   -> {top_str}")


if __name__ == "__main__":
    main()
