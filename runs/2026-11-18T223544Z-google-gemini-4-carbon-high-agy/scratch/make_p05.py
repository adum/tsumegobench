#!/usr/bin/env python3
"""Generate, verify, and originality-check outputs/problem-05.sgf (5-9 kyu, Black to play and kill)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p05_sgf() -> tuple[str, TsumegoSpec]:
    # Bottom-left corner/edge (cols a..g, rows o..s), 27 setup stones
    #   a b c d e f g
    # o X X X X X X .
    # p O O X X X X .
    # q . O O O O X X
    # r O O . . X O X
    # s O O O . . . X
    ab = [
        "ao", "bo", "co", "do", "eo", "fo",
        "cp", "dp", "ep", "fp",
        "fq", "gq",
        "er", "gr",
        "gs",
    ]
    aw = [
        "ap", "bp",
        "bq", "cq", "dq", "eq",
        "ar", "br", "fr",
        "as", "bs", "cs",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["aq", "cr", "dr", "ds", "es", "fs"]
    cap_pts = ["er", "fr"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~(1 << sgf_to_pt("er"))
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )

    # Also check 2. W[es] and 2. W[fs] after 1. B[dr]:
    # - If 2. W[es]: 3. B[fs]C[RIGHT] (captures fr, connects to gs, dr-er has lib cr/ds? Wait: let solver check!)
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;B[dr]"
        f"(;W[cr]"
        f"(;B[es];W[ds];B[fs]C[RIGHT])"
        f"(;B[fs]"
        f"(;W[ds](;B[es]C[RIGHT])(;B[fr]C[RIGHT]))"
        f"(;W[es](;B[ds]C[RIGHT])(;B[fr]C[RIGHT]))))"
        f"(;W[ds]"
        f"(;B[es];W[cr];B[fs]C[RIGHT])"
        f"(;B[fs]"
        f"(;W[cr](;B[es]C[RIGHT])(;B[fr]C[RIGHT]))"
        f"(;W[es];B[fr]C[RIGHT])))"
        f"(;W[es];B[fs]"
        f"(;W[cr](;B[ds]C[RIGHT])(;B[fr]C[RIGHT]))"
        f"(;W[ds];B[fr]C[RIGHT])))"
        f"(;B[fs];W[dr])"
        f"(;B[es];W[dr])"
        f"(;B[ds];W[dr])"
        f"(;B[cr];W[dr]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p05_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=24)
    print("P05 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P05 failed verification!"

    out_path = ROOT / "outputs/problem-05.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P05 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p05-author-1", "outputs/problem-05.sgf")
    print("P05 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
