#!/usr/bin/env python3
"""
Generate, semantically verify, and originality-check outputs/problem-10.sgf
(Target: about 1 dan+, White to play and LIVE via 1-stone throw-in miai between
a 3-stone snapback and a 6-stone oiotoshi at a previously illegal-suicide point!).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p10_sgf() -> tuple[str, TsumegoSpec]:
    # Stepped L+belly top-left shape (cols a..i, rows a..e):
    # Add `gc = .` (`fc=O, fd=O, gd=O`, enclosed by `ed=X, fe,ge=X, hd,ic,hc=X`) so White ALSO has tempting `1.W[gc]`,
    # while `db, eb` still only has liberties `cb, da, ea`!
    grid = [
        "OOO..XX.X",  # a(0): aa,ba,ca=O; da,ea=.; fa,ga=X, ha=., ia=X
        ".O.XXOOXX",  # b(1): ab=., bb=O, cb=.; db,eb=X; fb,gb=O; hb,ib=X
        ".OOOOO.XX",  # c(2): ac=.; bc..fc=O, gc=.; hc,ic=X
        "OOXXXOOXX",  # d(3): ad,bd=O; cd..ed=X; fd,gd=O; hd,id=X
        "XX,,,XX,,",  # e(4): ae,be=X; fe,ge=X
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
    cap_pts = ["db", "eb", "fa", "ga", "fb", "gb"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["db", "eb", "fa", "ga"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=26)
    print("P10 1st moves:", [(m, TsumegoSolver.OUTCOME_NAMES[v]) for m, v in sol.analyze_moves(b, w, "W") if m not in ("ab", "ac")])

    # Verify exact branches after 1. W[ea]:
    # - 2. B[da] (captures 1.W[ea]!) -> 3. W[cb] (unique! Puts da-db-eb in 1-lib snapback atari at ea!)
    #   - 4. B[ea] (connects da-db-eb-ea-fa-ga into 6-stone clump with ONLY 1 lib ha!) -> 5. W[ha]C[RIGHT] (captures all 6 stones!)
    #   - 4. B[ha] (connects fa-ga out to ia-hb!) -> 5. W[ea]C[RIGHT] (recaptures da,db,eb in snapback!)
    #   - 4. B[gc] (atari/poke on right!) -> 5. W[ea]C[RIGHT] (recaptures da,db,eb in snapback, saving everything!)
    # - 2. B[ha] (connects fa-ga out without capturing ea!) -> (3. W[da]C[RIGHT]) | (3. W[cb]; 4. B[da]; 5. W[ea]C[RIGHT])
    # - 2. B[gc] (cuts fb-gb in 2 libs? Check!) -> let solver tell us exact winning 3.W moves!
    b1, w1, k1 = play_move(b, w, "W", sgf_to_pt("ea"))
    for m2 in ["da", "ha", "gc", "cb"]:
        res2 = play_move(b1, w1, "B", sgf_to_pt(m2), k1)
        if res2 is None:
            continue
        b2, w2, k2 = res2
        w3 = [m for m, v in sol.analyze_moves(b2, w2, "W", k2) if v == 4 and m not in ("ab", "ac")]
        print(f"  After 1.W[ea] 2.B[{m2}], 3.W wins: {w3}")

    # Also check wrong 1st moves:
    for wm in ["da", "cb", "gc"]:
        wb, ww, wk = play_move(b, w, "W", sgf_to_pt(wm))
        breps = [m for m, v in sol.analyze_moves(wb, ww, "B", wk) if v < 4 and m not in ("ab", "ac")]
        print(f"  Wrong 1.W[{wm}] -> B refutes with: {breps}")

    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[ea]"
        f"(;B[da]"
        f"(;W[cb]"
        f"(;B[ea];W[ha]C[RIGHT])"
        f"(;B[ha];W[ea]C[RIGHT])"
        f"(;B[gc];W[ea]C[RIGHT]))"
        f"(;W[gc];B[ea]))"
        f"(;B[ha]"
        f"(;W[da]C[RIGHT])"
        f"(;W[cb];B[da];W[ea]C[RIGHT])"
        f"(;W[gc];B[da]))"
        f"(;B[gc]"
        f"(;W[da]C[RIGHT])"
        f"(;W[ha]C[RIGHT])"
        f"(;W[cb];B[da];W[ea]C[RIGHT])))"
        f"(;W[da];B[ea])"
        f"(;W[cb];B[ea])"
        f"(;W[gc];B[ea]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p10_sgf()
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

    res = query_originality("p10-author-1", "outputs/problem-10.sgf")
    print("P10 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
