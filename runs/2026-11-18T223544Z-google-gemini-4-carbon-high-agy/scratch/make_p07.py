#!/usr/bin/env python3
"""Verify & originality-check outputs/problem-07.sgf, and test the 7-move oiotoshi squeeze for P08!"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality
from design_p07_p08 import analyze_deep

ROOT = Path(__file__).resolve().parent.parent


def build_p07_sgf() -> tuple[str, TsumegoSpec]:
    # Bottom-right corner/edge (cols l..s, rows n..s), 1-4 kyu Black to play and kill (7 moves!)
    #   l m n o p q r s
    # n . . . . . . X X
    # o . X X X X X X .
    # p X X X O O O O O
    # q X X O O O O O O
    # r X O . X X O O O
    # s X O . . . O O .
    ab = [
        "rn", "sn",
        "mo", "no", "oo", "po", "qo", "ro",
        "lp", "mp", "np",
        "lq", "mq",
        "lr", "or", "pr",
        "ls",
    ]
    aw = [
        "op", "pp", "qp", "rp", "sp",
        "nq", "oq", "pq", "qq", "rq", "sq",
        "mr", "qr", "rr", "sr",
        "ms", "qs", "rs",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["so", "nr", "ns", "os", "ps", "ss"]
    cap_pts = ["mr", "ms", "or", "pr"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["or", "pr"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )

    # Complete, verified 5-to-7 move tree for 1. B[nr]:
    # - 2. W[ns] -> 3. B[os] (captures mr,ms,ns!)
    #    - 4. W[mr] -> (5. B[ms]C[RIGHT]) | (5. B[ns]; 6. W[ps]; 7. B[ms]C[RIGHT])
    #    - 4. W[ns] -> (5. B[mr]C[RIGHT]) | (5. B[ms]; 6. W[ps](;B[mr]C[RIGHT])(;B[ns]C[RIGHT]))
    #    - 4. W[ps] -> (5. B[mr]C[RIGHT]) | (5. B[ns](;W[mr];B[ms]C[RIGHT])(;W[ms];B[mr]C[RIGHT]))
    # - 2. W[os] -> 3. B[ns] (captures mr,ms!)
    #    - 4. W[mr] -> (5. B[ms]C[RIGHT]) | (5. B[ps]C[RIGHT])
    #    - 4. W[ms] -> (5. B[mr]C[RIGHT]) | (5. B[ps]C[RIGHT])
    #    - 4. W[ps] -> (5. B[mr]C[RIGHT]) | (5. B[ms]C[RIGHT])
    # - 2. W[ps] -> 3. B[ns] (captures mr,ms!)
    #    - 4. W[mr] -> 5. B[ms]C[RIGHT]
    #    - 4. W[ms] -> 5. B[mr]C[RIGHT]
    #    - 4. W[os] -> (5. B[mr]C[RIGHT]) | (5. B[ms]C[RIGHT])
    # Wrong first moves:
    # - 1. B[ns] -> 2. W[nr]
    # - 1. B[os] -> 2. W[nr]
    # - 1. B[ps] -> 2. W[nr]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;B[nr]"
        f"(;W[ns];B[os]"
        f"(;W[mr](;B[ms]C[RIGHT])(;B[ns];W[ps];B[ms]C[RIGHT]))"
        f"(;W[ns](;B[mr]C[RIGHT])(;B[ms];W[ps](;B[mr]C[RIGHT])(;B[ns]C[RIGHT])))"
        f"(;W[ps](;B[mr]C[RIGHT])(;B[ns](;W[mr];B[ms]C[RIGHT])(;W[ms];B[mr]C[RIGHT]))))"
        f"(;W[os];B[ns]"
        f"(;W[mr](;B[ms]C[RIGHT])(;B[ps]C[RIGHT]))"
        f"(;W[ms](;B[mr]C[RIGHT])(;B[ps]C[RIGHT]))"
        f"(;W[ps](;B[mr]C[RIGHT])(;B[ms]C[RIGHT])))"
        f"(;W[ps];B[ns]"
        f"(;W[mr];B[ms]C[RIGHT])"
        f"(;W[ms];B[mr]C[RIGHT])"
        f"(;W[os](;B[mr]C[RIGHT])(;B[ms]C[RIGHT]))))"
        f"(;B[ns];W[nr])"
        f"(;B[os];W[nr])"
        f"(;B[ps];W[nr]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
    # First test P08 oiotoshi squeeze candidates!
    print("=== Testing P08 7-move Oiotoshi Squeeze Candidates ===")
    analyze_deep("P08-oiotoshi-1", [
        ".O....XX,",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=X, ha=X
        "OOOXXOXX,",  # b(1): ab=O, bb=O, cb=O, db=X, eb=X, fb=O, gb=X, hb=X
        "XXXO.OXX,",  # c(2): ac,bc,cc=X; dc=O, ec=., fc=O; gc,hc=X
        ",,,XXXX,,",  # d(3): dd..gd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fb", "fc"])

    analyze_deep("P08-oiotoshi-2", [
        ".O.....XX",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=., ha=X, ia=X
        "OOOXXOOXX",  # b(1): ab..cb=O; db,eb=X; fb,gb=O; hb,ib=X
        "XXXO.XOXX",  # c(2): ac..cc=X; dc=O, ec=., fc=X, gc=O; hc,ic=X? Keep fc=O!
    ][:2] + [
        "XXXOO.OXX",  # c(2): ac..cc=X; dc,ec=O, fc=., gc=O; hc,ic=X
        ",,,XXXXX,",  # d(3): dd..hd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fb", "gb", "gc"])

    # Now verify and submit P07!
    print("\n=== Verifying and Querying P07 ===")
    sgf, spec = build_p07_sgf()
    ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=26)
    print("P07 tree verification:", ok)
    for e in errs:
        print("  ERR:", e)
    for n in notes:
        print("  NOTE:", n)
    assert ok, "P07 failed verification!"

    out_path = ROOT / "outputs/problem-07.sgf"
    out_path.write_text(sgf, encoding="utf-8")
    v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(sgf)
    print("P07 validator:", v_ok, v_errs, v_warns, v_info)
    assert v_ok and not v_warns

    res = query_originality("p07-author-1", "outputs/problem-07.sgf")
    print("P07 originality:", res["status"], "topPct:", res["goProblems"]["topPercentage"], "sigMatches:", len(res["goProblems"]["signatureMatches"]), "rem:", res["queriesRemaining"])
    if res["status"] != "clear":
        print(json.dumps(res, indent=2))
    else:
        print("Top 3:", res["goProblems"]["percentageMatches"][:3])
