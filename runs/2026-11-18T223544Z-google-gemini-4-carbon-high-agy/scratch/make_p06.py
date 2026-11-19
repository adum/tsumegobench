#!/usr/bin/env python3
"""Generate, verify, and originality-check outputs/problem-06.sgf (5-9 kyu, pure center White to kill)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSpec, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p06_sgf() -> tuple[str, TsumegoSpec]:
    # Pure floating center group (cols f..l, rows f..k — zero 1st/2nd/3rd/4th line edges!)
    #   f g h i j k l
    # f . O O O O O .
    # g O X X X X O O
    # h O X . X . X O
    # i O X X . . . O
    # j O O X X X O O
    # k . . O O O . .
    # Note: connect fg-fh-fi-fj-gj to hk-ik-jk via gk=O, and gf-hf-if-jf-kf to kg-lg-lh-li-lj-kj via kk=O
    # and fg to gf via ff=O? Even cleaner: gf=O touches fg=O? (f,g) and (g,f) are diagonal! Add ff=O? Or fg,gg?
    # Check White wall connectivity:
    # Top: gf, hf, if, jf, kf -> kf touches kg (connected to lg-lh-li-lj-kj!).
    # Bottom: hk, ik, jk -> jk touches jj=X, kj=O -> add kk=O to connect jk-kk-kj!
    # Left: fg, fh, fi, fj, gj -> add gk=O to connect gj-gk-hk, and ff=O to connect fg-ff-gf!
    # That makes the ENTIRE White outer ring ONE single 22-stone connected chain with ~24 outside liberties!
    ab = [
        "gg", "hg", "ig", "jg",
        "gh", "ih", "kh",
        "gi", "hi",
        "hj", "ij", "jj",
    ]
    aw = [
        "ff", "gf", "hf", "if", "jf", "kf",
        "fg", "kg", "lg",
        "fh", "lh",
        "fi", "li",
        "fj", "gj", "kj", "lj",
        "gk", "hk", "ik", "jk", "kk",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["hh", "jh", "ii", "ji", "ki"]
    cap_pts = ["kh"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    outside = BOARD_MASK ^ (combat | b)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="B",
        target_stones=b, combat_mask=combat,
        outside_mask=outside, immortal_attacker=w,
    )

    # Winning mid-air placement 1. W[ji]:
    # - 2. B[jh] -> 3. W[ki]C[RIGHT]
    # - 2. B[ki] -> 3. W[jh]C[RIGHT]
    # - 2. B[ii] -> (3. W[ki]C[RIGHT]) | (3. W[jh]; 4. B[ki])  <-- also show why 3.W[jh] fails after 2.B[ii]!
    # Wrong first moves:
    # - 1. W[jh] -> 2. B[ji]
    # - 1. W[ki] -> 2. B[ji]
    # - 1. W[ii] -> 2. B[ji]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[ji]"
        f"(;B[jh];W[ki]C[RIGHT])"
        f"(;B[ki];W[jh]C[RIGHT])"
        f"(;B[ii]"
        f"(;W[ki]C[RIGHT])"
        f"(;W[jh];B[ki])))"
        f"(;W[jh];B[ji])"
        f"(;W[ki];B[ji])"
        f"(;W[ii];B[ji]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p06_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=22)
    print("P06 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P06 failed verification!"

    out_path = ROOT / "outputs/problem-06.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P06 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p06-author-1", "outputs/problem-06.sgf")
    print("P06 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
