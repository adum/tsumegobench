#!/usr/bin/env python3
"""Generate, verify, and originality-check outputs/problem-09.sgf (about 1 dan, Black to kill in 7 moves)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p09_sgf() -> tuple[str, TsumegoSpec]:
    # Upper-right corner/edge (cols k..s, rows a..d), 25 setup stones
    #   k l m n o p q r s
    # a X . . O . . O . .   (ka=X, la=., ma=., na=O, oa=., pa=., qa=O, ra=., sa=.)
    # b X X O . X X O O O   (kb,lb=X; mb=O, nb=., ob=X, pb=X; qb,rb,sb=O)
    # c . X X O O O O O X   (lc,mc=X; nc..rc=O; sc=X)
    # d . . . X X X X X X   (nd..sd = X)
    ab = [
        "ka",
        "kb", "lb", "ob", "pb",
        "lc", "mc", "sc",
        "nd", "od", "pd", "qd", "rd", "sd",
    ]
    aw = [
        "na", "qa",
        "mb", "qb", "rb", "sb",
        "nc", "oc", "pc", "qc", "rc",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["la", "ma", "oa", "pa", "ra", "sa", "nb"]
    cap_pts = ["na", "mb", "ob", "pb"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["ob", "pb"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )

    # Check wrong-move refutations with solver to pick cleanest refuting replies:
    sol = TsumegoSolver(spec, max_depth=26)
    for wm in ["ma", "la", "oa", "pa"]:
        nb, nw, nk = play_move(b, w, "B", sgf_to_pt(wm))
        print(f"Wrong 1.B[{wm}] -> W living replies:", [m for m,v in sol.analyze_moves(nb, nw, "W", nk) if v == 4])

    # Also check wrong 3rd moves after 1.B[nb] 2.W[ma] (e.g. 3.B[oa] or 3.B[pa]) and after 1.B[nb] 2.W[oa] (e.g. 3.B[pa]):
    b1, w1, k1 = play_move(b, w, "B", sgf_to_pt("nb"))
    b2m, w2m, k2m = play_move(b1, w1, "W", sgf_to_pt("ma"), k1)
    for m3w in ["oa", "pa"]:
        b3w, w3w, k3w = play_move(b2m, w2m, "B", sgf_to_pt(m3w), k2m)
        print(f"After 1.B[nb] 2.W[ma] wrong 3.B[{m3w}] -> W wins:", [m for m,v in sol.analyze_moves(b3w, w3w, "W", k3w) if v == 4])
    b2o, w2o, k2o = play_move(b1, w1, "W", sgf_to_pt("oa"), k1)
    

    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;B[nb]"
        f"(;W[ma]"
        f"(;B[la]"
        f"(;W[oa];B[pa]C[RIGHT])"
        f"(;W[pa];B[oa]"
        f"(;W[mb];B[ma]C[RIGHT])"
        f"(;W[na](;B[ma]C[RIGHT])(;B[mb]C[RIGHT]))))"
        f"(;B[oa];W[pa])"
        f"(;B[pa];W[oa]))"
        f"(;W[oa]"
        f"(;B[ma];W[pa];B[mb]C[RIGHT])"
        f"(;B[la];W[pa]))"
        f"(;W[pa]"
        f"(;B[ma];W[oa];B[mb]C[RIGHT])"
        f"(;B[la];W[oa])))"
        f"(;B[ma];W[nb])"
        f"(;B[la];W[nb])"
        f"(;B[oa];W[nb])"
        f"(;B[pa];W[nb]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p09_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=26)
    print("P09 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P09 failed verification!"

    out_path = ROOT / "outputs/problem-09.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P09 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p09-author-1", "outputs/problem-09.sgf")
    print("P09 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
