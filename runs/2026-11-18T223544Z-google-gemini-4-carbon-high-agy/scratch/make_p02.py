#!/usr/bin/env python3
"""Generate outputs/problem-02.sgf, verify against TsumegoSolver, and check originality."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p02_sgf() -> tuple[str, TsumegoSpec]:
    # Bottom edge (shifted away from corners: cols i..q, rows p..s)
    #   i j k l m n o p q
    # p . . . O O O O O .
    # q . O O X X X X O O
    # r O X . . X X X X O
    # s O X X . X X . X O
    # Note: connect White's left wall (ir, is, jq, kq) to top wall (lp..pp) via kp=O so White is 1 single 14-stone chain!
    ab = [
        "lq", "mq", "nq", "oq",
        "jr", "mr", "nr", "or", "pr",
        "js", "ks", "ms", "ns", "ps",
    ]
    aw = [
        "kp", "lp", "mp", "np", "op", "pp",
        "jq", "kq", "pq",
        "ir", "qr",
        "is", "qs",
    ]

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["kr", "lr", "ls", "os"]
    cap_pts = ["jr", "js", "ks"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    outside = BOARD_MASK ^ (combat | b)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="B",
        target_stones=b, combat_mask=combat,
        outside_mask=outside, immortal_attacker=w,
    )

    ab_str = "".join(f"[{s}]" for s in ab)
    aw_str = "".join(f"[{s}]" for s in aw)

    # Check exact wrong lines first:
    # 1. W[lr] -> (2. B[kr]; 3. W[ls]C[RIGHT]) | (2. B[ls]; 3. W[kr]C[RIGHT])
    # 1. W[kr] -> 2. B[lr] (ko, whereas W[lr] kills unconditionally!)
    # 1. W[ls] -> 2. B[lr] (ko!)
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_str}AW{aw_str}"
        f"(;W[lr]"
        f"(;B[kr];W[ls]C[RIGHT])"
        f"(;B[ls];W[kr]C[RIGHT]))"
        f"(;W[kr];B[lr])"
        f"(;W[ls];B[lr]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p02_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=22)
    print("Tree verification ok:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "Verification failed!"

    out_path = ROOT / "outputs/problem-02.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(out_path.read_text(encoding="utf-8"))
    print("SGF validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p02-author-1", "outputs/problem-02.sgf")
    print("Originality result:")
    print(json.dumps(res, indent=2))
