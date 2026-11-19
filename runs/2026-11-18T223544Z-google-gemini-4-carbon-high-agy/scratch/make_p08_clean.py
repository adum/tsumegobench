#!/usr/bin/env python3
"""
Cleanly build, verify, and originality-check outputs/problem-08.sgf (1-4 kyu, White to live via 2-stone bait sacrifice),
and search 7-9 move 1-2 dan candidates for outputs/problem-10.sgf!
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSpec, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality
from search_dan import eval_dan

ROOT = Path(__file__).resolve().parent.parent


def build_p08_clean() -> tuple[str, TsumegoSpec]:
    grid = [
        ",XXXX",  # k(10): pk..sk = X
        ",XX.X",  # l(11): pl,ql=X, rl=., sl=X
        "XX..O",  # m(12): om,pm=X; qm,rm=.; sm=O
        "XOOX.",  # n(13): on=X; pn,qn=O; rn=X, sn=.
        "XOOXX",  # o(14): oo=X; po,qo=O; ro,so=X
        "XXOO.",  # p(15): op,pp=X; qp,rp=O; sp=.
        "XXOOO",  # q(16): oq,pq=X; qq..sq=O
        ",XOO.",  # r(17): pr=X; qr,rr=O; sr=.
        ",XOO.",  # s(18): ps=X; qs,rs=O; ss=.
    ]
    ab = []
    aw = []
    empty_pts = []
    for dr, row_s in enumerate(grid):
        for dc, ch in enumerate(row_s):
            c_str = chr(97 + 14 + dc) + chr(97 + 10 + dr)
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
    cap_pts = ["sm", "rn", "ro", "so"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["rn", "ro", "so"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )

    # Exact, clean 5-move directional bait-sacrifice tree:
    # 1. W[rm] (unique!)
    #   - 2. B[qm] (cuts off 2-stone bait sm-rm in atari!)
    #     - 3. W[sp] (unique! Ataris from below -> 4. B[rl] captures bait -> 5. W[sn]C[RIGHT] captures rn,ro,so!)
    #     - 3. W[sn] (wrong direction! -> 4. B[rl] captures sm-rm AND puts W[sn] in atari!)
    #   - 2. B[rl] (atari on sm-rm from top without cutting!)
    #     - 3. W[qm]C[RIGHT] (connects sm-rm to qn, making eye {rl} + {sr,ss}!)
    #     - 3. W[sp]; 4. B[qm]; 5. W[sn]C[RIGHT] (transposes to capturing rn,ro,so!)
    # Wrong first moves:
    #   - 1. W[qm]; 2. B[rm]
    #   - 1. W[sn]; 2. B[qm]
    #   - 1. W[sp]; 2. B[rm]
    #   - 1. W[rl]; 2. B[qm]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[rm]"
        f"(;B[qm]"
        f"(;W[sp];B[rl];W[sn]C[RIGHT])"
        f"(;W[sn];B[rl]))"
        f"(;B[rl]"
        f"(;W[qm]C[RIGHT])"
        f"(;W[sp];B[qm];W[sn]C[RIGHT])))"
        f"(;W[qm];B[rm])"
        f"(;W[sn];B[qm])"
        f"(;W[sp];B[rm])"
        f"(;W[rl];B[qm]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    print("=== Verifying & Checking Originality of P08 ===")
    sgf8, spec8 = build_p08_clean()
    ok8, errs8, notes8 = verify_tree_against_solver(sgf8, spec8, max_depth=26)
    print("P08 tree verification:", ok8)
    for e in errs8:
        print("  ERR:", e)
    for n in notes8:
        print("  NOTE:", n)
    assert ok8

    out8 = ROOT / "outputs/problem-08.sgf"
    out8.write_text(sgf8, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf8)
    print("P08 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res8 = query_originality("p08-author-2", "outputs/problem-08.sgf")
    print("P08 originality:", res8["status"], "topPct:", res8["goProblems"]["topPercentage"], "sigMatches:", len(res8["goProblems"]["signatureMatches"]), "rem:", res8["queriesRemaining"])
    if res8["status"] != "clear":
        print(json.dumps(res8, indent=2))
    else:
        print("Top 3:", res8["goProblems"]["percentageMatches"][:3])

    print("\n=== Searching 7-9 Move 1-2 Dan Top-Left Candidates for P10 ===")
    eval_dan("P10-TL-kill-2", [
        "..X..X..O",  # a(0): aa,ba=.; ca=X; da,ea=.; fa=X; ga,ha=.; ia=O
        "XXX.OOXXO",  # b(1): ab..cb=X, db=.; eb,fb=O; gb,hb=X; ib=O
        "OOOXXXOO,",  # c(2): ac..cc=O; dc..fc=X; gc,hc=O
        ",,OOOOO,,",  # d(3): cd..gd = O
    ], r0=0, c0=0, first="W", defender="B", cap_coords=["eb", "fb", "gb", "hb"], ignore_pts={"aa", "ba"})

    eval_dan("P10-TL-live-3", [
        "..O..O..X",  # a(0)
        "OOO.XXOOX",  # b(1)
        "XXOOOO.XX",  # c(2)
        ",,XXXXOXX",  # d(3)
        ",,,,,XXX,",  # e(4)
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["eb", "fb", "fa", "gd"], ignore_pts={"aa", "ba"})
