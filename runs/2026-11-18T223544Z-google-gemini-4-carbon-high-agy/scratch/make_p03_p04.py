#!/usr/bin/env python3
"""Generate, semantically verify, and originality-check outputs/problem-03.sgf and outputs/problem-04.sgf."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSpec, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p03_sgf() -> tuple[str, TsumegoSpec]:
    # Target: 10-19 kyu (~13-15 kyu), Black to play and live (top edge, cols e..m, rows a..f)
    # Shift P03-false-eye-trap from c0=9 (j..r) to c0=4 (e..m):
    #   e f g h i j k l m
    # a O O O . . X . X O   (ea,fa,ga = O; ha=., ia=.; ja=X, ka=., la=X; ma=O)
    # b O X X . X X X X O   (eb=O; fb,gb=X; hb=.; ib,jb,kb,lb=X; mb=O)
    # c O . X O X O O O O   (ec=O; fc=.; gc=X; hc=O; ic=X; jc,kc,lc,mc=O)
    # d O O O X O O . . .   (ed,fd,gd=O; hd=X; id,jd=O)
    # e . . O . O . . . .   (ge=O; he=.; ie=O)
    # f . . . O . . . . .   (hf=O)
    ab = [
        "ja", "la",
        "fb", "gb", "ib", "jb", "kb", "lb",
        "gc", "ic",
        "hd",
    ]
    aw = [
        "ea", "fa", "ga", "ma",
        "eb", "mb",
        "ec", "hc", "jc", "kc", "lc", "mc",
        "ed", "fd", "gd", "id", "jd",
        "ge", "ie",
        "hf",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    # Winning line:
    # 1. B[ha] -> (2. W[fc]; 3. B[hb]C[RIGHT]) | (2. W[he]; 3. B[hb]C[RIGHT])
    # Plausible wrong first moves:
    # 1. B[hb] (greedy capture of W[hc]!) -> 2. W[ha]
    #    - 3. B[ia] -> 4. W[he] (captures B[hd], turning {hc} into false/ko eye!)
    #    - 3. B[hc] -> 4. W[ia] (only 1 eye {ka}!)
    #    - 3. B[fc] -> 4. W[he]
    # 1. B[ia] -> 2. W[hb]
    # 1. B[fc] -> 2. W[ha] (or 2. W[hb]? Let's check with solver: in P03-false-eye-trap, after 1.B[fc], W[ha] -> KO/DEAD!)
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;B[ha]"
        f"(;W[fc];B[hb]C[RIGHT])"
        f"(;W[he];B[hb]C[RIGHT]))"
        f"(;B[hb];W[ha]"
        f"(;B[ia];W[he])"
        f"(;B[hc];W[ia])"
        f"(;B[fc];W[he]))"
        f"(;B[ia];W[hb])"
        f"(;B[fc];W[ha]))\n"
    )

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["ha", "ia", "ka", "hb", "fc", "he"]
    cap_pts = ["fb", "gb", "gc", "hc", "hd"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = w & ~(1 << sgf_to_pt("hc"))
    outside = BOARD_MASK ^ (combat | b)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="B",
        target_stones=b, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    return sgf, spec


def build_p04_sgf() -> tuple[str, TsumegoSpec]:
    # Target: 10-19 kyu (~11-13 kyu), White to play and live in 5 moves (right edge, cols o..s, rows d..j)
    #   o p q r s
    # d . . . X X
    # e . . X O .
    # f . X X O .
    # g X X O . .
    # h X O . . O
    # i X O O O X
    # j . X X X X
    ab = [
        "rd", "sd",
        "qe",
        "pf", "qf",
        "og", "pg",
        "oh",
        "oi", "si",
        "pj", "qj", "rj", "sj",
    ]
    aw = [
        "re", "rf",
        "qg",
        "ph", "sh",
        "pi", "qi", "ri",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    # Winning 5-move miai junction 1. W[rg]:
    # - 2. B[qh] -> 3. W[rh] -> (4. B[se]; 5. W[sf]C[RIGHT]) | (4. B[sf]; 5. W[se]C[RIGHT])
    # - 2. B[rh] -> 3. W[qh] -> (4. B[se]; 5. W[sf]C[RIGHT]) | (4. B[sf]; 5. W[se]C[RIGHT]) | (4. B[sg]; 5. W[sf]C[RIGHT])
    # - 2. B[se] -> 3. W[sf] -> (4. B[qh]; 5. W[rh]C[RIGHT]) | (4. B[rh]; 5. W[qh]C[RIGHT])
    # - 2. B[sf] -> 3. W[se] -> (4. B[qh]; 5. W[rh]C[RIGHT]) | (4. B[rh]; 5. W[qh]C[RIGHT])
    # - 2. B[sg] -> (3. W[sf]; 4. B[qh]; 5. W[rh]C[RIGHT]) | (3. W[sf]; 4. B[rh]; 5. W[qh]C[RIGHT]) | (3. W[rh]; 4. B[sf]; 5. W[se]C[RIGHT]) | (3. W[rh]; 4. B[se]; 5. W[sf]C[RIGHT])
    # Wrong first moves:
    # - 1. W[rh] -> 2. B[sf] -> (3. W[rg]; 4. B[se]) | (3. W[se]; 4. B[rg]) | (3. W[sg]; 4. B[rg])
    # - 1. W[sf] -> 2. B[rh]
    # - 1. W[se] -> 2. B[rh]
    # - 1. W[qh] -> 2. B[sg]
    # - 1. W[sg] -> 2. B[rh]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[rg]"
        f"(;B[qh];W[rh](;B[se];W[sf]C[RIGHT])(;B[sf];W[se]C[RIGHT]))"
        f"(;B[rh];W[qh](;B[se];W[sf]C[RIGHT])(;B[sf];W[se]C[RIGHT])(;B[sg];W[sf]C[RIGHT]))"
        f"(;B[se];W[sf](;B[qh];W[rh]C[RIGHT])(;B[rh];W[qh]C[RIGHT]))"
        f"(;B[sf];W[se](;B[qh];W[rh]C[RIGHT])(;B[rh];W[qh]C[RIGHT]))"
        f"(;B[sg]"
        f"(;W[sf](;B[qh];W[rh]C[RIGHT])(;B[rh];W[qh]C[RIGHT]))"
        f"(;W[rh](;B[se];W[sf]C[RIGHT])(;B[sf];W[se]C[RIGHT]))))"
        f"(;W[rh];B[sf]"
        f"(;W[rg];B[se])"
        f"(;W[se];B[rg])"
        f"(;W[sg];B[se]))"
        f"(;W[sf];B[rh])"
        f"(;W[se];B[rh])"
        f"(;W[qh];B[sg])"
        f"(;W[sg];B[rh]))\n"
    )

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["se", "sf", "rg", "sg", "qh", "rh"]
    cap_pts = ["re", "rf", "sh"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="W", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=b,
    )
    return sgf, spec


if __name__ == "__main__":
    for num, builder in [("03", build_p03_sgf), ("04", build_p04_sgf)]:
        print(f"=== Verifying problem-{num} ===")
        sgf, spec = builder()
        ok, errs, notes = verify_tree_against_solver(sgf, spec, max_depth=24)
        print("  Tree verification ok:", ok)
        for e in errs:
            print("   ERR:", e)
        for n in notes:
            print("   NOTE:", n)
        assert ok, f"problem-{num} failed solver verification!"

        out_path = ROOT / f"outputs/problem-{num}.sgf"
        out_path.write_text(sgf, encoding="utf-8")
        v_ok, v_errs, v_warns, v_info = validate_sgf_candidate(out_path.read_text(encoding="utf-8"))
        print("  SGF validator:", v_ok, v_errs, v_warns, v_info)
        assert v_ok and not v_warns

        res = query_originality(f"p{num}-author-1", f"outputs/problem-{num}.sgf")
        print(f"  Originality status: {res['status']} (topPct={res['goProblems']['topPercentage']}, sigMatches={len(res['goProblems']['signatureMatches'])}, rem={res['queriesRemaining']})")
        if res["status"] != "clear":
            print(json.dumps(res, indent=2))
        else:
            top3 = res["goProblems"]["percentageMatches"][:3]
            print("  Top 3 GP matches:", top3)
