#!/usr/bin/env python3
"""Generate outputs/problem-01.sgf, run full semantic tree verification, and check originality."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSpec, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import local_precheck, query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p01_sgf() -> tuple[str, TsumegoSpec]:
    # Left edge, rows d..j, cols a..d (20 setup stones)
    #   a b c d
    # d O O O .
    # e X X O .
    # f . X O .
    # g X X X O
    # h . O . O
    # i . X X O
    # j O O O O
    ab = ["ae", "be", "bf", "ag", "bg", "cg", "bi", "ci"]
    aw = ["ad", "bd", "cd", "ce", "cf", "dg", "bh", "dh", "di", "aj", "bj", "cj", "dj"]

    ab_str = "".join(f"[{s}]" for s in ab)
    aw_str = "".join(f"[{s}]" for s in aw)

    # Tree:
    # 1. B[ch] -> (2. W[ah] -> 3. B[ai]C[RIGHT]) | (2. W[ai] -> 3. B[ah]C[RIGHT])
    # 1. B[ah] -> 2. W[ch]
    # 1. B[ai] -> 2. W[ch]
    # 1. B[af] -> 2. W[ch]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_str}AW{aw_str}"
        f"(;B[ch]"
        f"(;W[ah];B[ai]C[RIGHT])"
        f"(;W[ai];B[ah]C[RIGHT]))"
        f"(;B[ah];W[ch])"
        f"(;B[ai];W[ch])"
        f"(;B[af];W[ch]))\n"
    )

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["af", "ah", "ch", "ai"]
    cap_pts = ["bh", "bi", "ci"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = w & ~(1 << sgf_to_pt("bh"))
    outside = BOARD_MASK ^ (combat | b)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="B",
        target_stones=b, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p01_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=20)
    print("Tree verification ok:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "Verification failed!"

    out_path = ROOT / "outputs/problem-01.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(out_path.read_text(encoding="utf-8"))
    print("SGF validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p01-author-1", "outputs/problem-01.sgf")
    print("Originality result:")
    print(json.dumps(res, indent=2))
