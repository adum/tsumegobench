#!/usr/bin/env python3
"""Generate, verify, and originality-check outputs/problem-08.sgf (1-4 kyu, White to live via oiotoshi/snapback squeeze)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, opp_color, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def auto_build_right_subtree(sol: TsumegoSolver, b: int, w: int, ko: int | None, prot: str, target_v: int, ignore_pts: set[str], depth: int = 1) -> str:
    """
    Build exact minimal-yet-complete SGF subtree after a protagonist move `(b, w, ko)`:
    - Checks which antagonist moves STILL pose a genuine threat (if prot passed, ant would break `target_v`).
    - If no antagonist move poses a real threat (or depth >= 9), marks `C[RIGHT]` right here!
    - Otherwise, branches on every real antagonist defense, and at the next protagonist turn
      includes EVERY winning protagonist move so Rule 5 is 100% satisfied!
    """
    ant = opp_color(prot)
    if depth >= 9 or sol.is_defender_clean_alive(b, w):
        return "C[RIGHT]"

    threats = []
    for am, _ in sol.analyze_moves(b, w, ant, ko):
        if am in ignore_pts:
            continue
        nb, nw, nko = play_move(b, w, ant, sgf_to_pt(am), ko)
        if sol.evaluate(nb, nw, ant, None) != target_v:
            threats.append((am, nb, nw, nko))

    if not threats:
        return "C[RIGHT]"

    parts = []
    for am, nb, nw, nko in threats:
        # Find ALL winning protagonist replies
        pmoves = [pm for pm, pv in sol.analyze_moves(nb, nw, prot, nko) if pv == target_v and pm not in ignore_pts]
        assert pmoves, f"No winning reply to {ant}[{am}] at depth {depth}!"
        if len(pmoves) == 1:
            pm = pmoves[0]
            nb2, nw2, nko2 = play_move(nb, nw, prot, sgf_to_pt(pm), nko)
            tail = auto_build_right_subtree(sol, nb2, nw2, nko2, prot, target_v, ignore_pts, depth + 2)
            parts.append(f"(;{ant}[{am}];{prot}[{pm}]{tail})")
        else:
            sub = []
            for pm in pmoves:
                nb2, nw2, nko2 = play_move(nb, nw, prot, sgf_to_pt(pm), nko)
                tail = auto_build_right_subtree(sol, nb2, nw2, nko2, prot, target_v, ignore_pts, depth + 2)
                sub.append(f"(;{prot}[{pm}]{tail})")
            parts.append(f"(;{ant}[{am}]{''.join(sub)})")
    if len(parts) == 1:
        # Unwrap outer parens when single branch
        inner = parts[0][1:-1]
        return inner
    return "".join(parts)


def build_p08_sgf() -> tuple[str, TsumegoSpec]:
    # Top-left corner/edge (cols a..i, rows a..d), 26 setup stones
    #   a b c d e f g h i
    # a . O . . . . . X X   (aa=., ba=O, ca..ga=., ha=X, ia=X)
    # b O O O X X O O X X   (ab..cb=O; db,eb=X; fb,gb=O; hb,ib=X)
    # c X X O O . O O X X   (ac,bc=X; cc,dc=O; ec=.; fc,gc=O; hc,ic=X)
    # d . . X X X X X X .   (cd..hd = X)
    ab = [
        "ha", "ia",
        "db", "eb", "hb", "ib",
        "ac", "bc", "hc", "ic",
        "cd", "dd", "ed", "fd", "gd", "hd",
    ]
    aw = [
        "ba",
        "ab", "bb", "cb", "fb", "gb",
        "cc", "dc", "fc", "gc",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["aa", "ca", "da", "ea", "fa", "ga", "ec"]
    cap_pts = ["db", "eb", "fb", "gb", "fc", "gc"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["db", "eb"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=26)

    b1, w1, k1 = play_move(b, w, "W", sgf_to_pt("ec"))
    right_tail = auto_build_right_subtree(sol, b1, w1, k1, "W", 4, {"aa"}, depth=1)

    # Check best refutations of wrong 1st moves:
    wrong_branches = []
    for wm in ["da", "ea", "fa", "ga", "ca"]:
        wb, ww, wk = play_move(b, w, "W", sgf_to_pt(wm))
        breps = sol.analyze_moves(wb, ww, "B", wk)
        best_b = breps[0][0]
        print(f"Wrong 1.W[{wm}] -> 2.B[{best_b}] ({TsumegoSolver.OUTCOME_NAMES[breps[0][1]]})")
        wrong_branches.append(f"(;W[{wm}];B[{best_b}])")

    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[ec]{right_tail})"
        f"{''.join(wrong_branches)})\n"
    )
    return sgf, spec


if __name__ == "__main__":
    sgf, spec = build_p08_sgf()
    print("Generated SGF length:", len(sgf))
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=26)
    print("P08 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P08 failed verification!"

    out_path = ROOT / "outputs/problem-08.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P08 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p08-author-1", "outputs/problem-08.sgf")
    print("P08 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
