#!/usr/bin/env python3
"""
Generate, semantically verify, and originality-check outputs/problem-10.sgf
using Clamp-Kill-Stepped (top-left L-shape, White to play and kill via 2nd-line wedge + 1st-line placement).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p10_stepped() -> tuple[str, TsumegoSpec]:
    # Top-left stepped L-shape (cols a..h, rows a..e), 26 setup stones
    # Connect White's outer wall into ONE single connected chain (`ae,be,ce=O` connects `ae,be` to `cd..gd`,
    # and `hd=O` connects `gd` to `gc,hc,gb,hb,ha`!):
    grid = [
        "XX.X...O",  # a(0): aa,ba=X, ca=., da=X; ea,fa,ga=.; ha=O
        ".X.XXXOO",  # b(1): ab=., bb=X, cb=.; db..fb=X; gb,hb=O
        ".XOO..OO",  # c(2): ac=., bc=X; cc,dc=O; ec,fc=.; gc,hc=O
        "XXOOOOOO",  # d(3): ad,bd=X; cd..hd=O
        "OOO,,,,,",  # e(4): ae..ce=O
    ]
    ab = []
    aw = []
    empty_pts = []
    for dr, row_s in enumerate(grid):
        for dc, ch in enumerate(row_s):
            if ch == ",":
                continue
            c_str = chr(97 + dc) + chr(97 + dr)
            if ch == "X":
                ab.append(c_str)
            elif ch == "O":
                aw.append(c_str)
            elif ch == ".":
                empty_pts.append(c_str)

    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)
    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    cap_pts = ["da", "db", "eb", "fb"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    outside = BOARD_MASK ^ (combat | b)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="B",
        target_stones=b, combat_mask=combat,
        outside_mask=outside, immortal_attacker=w,
    )
    sol = TsumegoSolver(spec, max_depth=26)

    # Check all Black replies after 1.W[cb]:
    b1, w1, k1 = play_move(b, w, "W", sgf_to_pt("cb"))
    for m2, v2 in []:
        if m2 in ("ab", "ac"):
            continue
        b2, w2, k2 = play_move(b1, w1, "B", sgf_to_pt(m2), k1)
        pv = sol.evaluate(b2, w2, "B", None)
        w3 = [m for m, v in sol.analyze_moves(b2, w2, "W", k2) if v == 0 and m not in ("ab", "ac")]
        print(f"After 1.W[cb] 2.B[{m2}] (pass={TsumegoSolver.OUTCOME_NAMES[pv]}), 3.W wins: {w3}")
        for m3 in w3:
            b3, w3b, k3 = play_move(b2, w2, "W", sgf_to_pt(m3), k2)
            for m4, _ in sol.analyze_moves(b3, w3b, "B", k3):
                if m4 in ("ab", "ac"):
                    continue
                b4, w4, k4 = play_move(b3, w3b, "B", sgf_to_pt(m4), k3)
                if sol.evaluate(b4, w4, "B", None) != 0:
                    w5 = [m for m, v in sol.analyze_moves(b4, w4, "W", k4) if v == 0 and m not in ("ab", "ac")]
                    print(f"   3.W[{m3}] 4.B[{m4}] -> 5.W wins: {w5}")

    # Check wrong 3rd moves after 1.W[cb] 2.B[ca]:
    b2c, w2c, k2c = play_move(b1, w1, "B", sgf_to_pt("ca"), k1)
    for wm3 in ["ea", "ga", "ec", "fc"]:
        b3w, w3w, k3w = play_move(b2c, w2c, "W", sgf_to_pt(wm3), k2c)
        breps = [m for m, v in sol.analyze_moves(b3w, w3w, "B", k3w) if v == 4]
        print(f"  After 1.W[cb] 2.B[ca] wrong 3.W[{wm3}] -> B lives with: {breps}")

    # Check wrong 1st moves:
    for wm1 in ["fa", "ca", "ea", "ga", "ec", "fc"]:
        wb, ww, wk = play_move(b, w, "W", sgf_to_pt(wm1))
        breps = [m for m, v in sol.analyze_moves(wb, ww, "B", wk) if v == 4]
        print(f"  Wrong 1.W[{wm1}] -> B lives with: {breps}")

    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[cb]"
        f"(;B[ca]"
        f"(;W[fa];B[ea];W[ga]C[RIGHT])"
        f"(;W[ea];B[fa])"
        f"(;W[ga];B[fa])"
        f"(;W[ec];B[fa]))"
        f"(;B[fa];W[ca]C[RIGHT]))"
        f"(;W[fa];B[cb])"
        f"(;W[ec];B[cb])"
        f"(;W[fc];B[cb])"
        f"(;W[ca];B[cb])"
        f"(;W[ea];B[cb])"
        f"(;W[ga];B[cb]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p10_stepped()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=26)
    print("P10 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P10 failed verification!"

    out_path = ROOT / "outputs/problem-10.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P10 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p10-author-2", "outputs/problem-10.sgf")
    print("P10 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
