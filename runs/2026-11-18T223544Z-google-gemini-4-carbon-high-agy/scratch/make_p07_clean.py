#!/usr/bin/env python3
"""Verify & originality-check outputs/problem-07.sgf (1-4 kyu, Black to kill vianr + outside liberty squeeze lr)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality

ROOT = Path(__file__).resolve().parent.parent


def build_p07_sgf() -> tuple[str, TsumegoSpec]:
    # Bottom-right corner/edge (cols k..s, rows o..s), 30 setup stones
    #   k l m n o p q r s
    # o . . X X X X X X X   (mo..so = X)
    # p . X X X O O O O O   (lp..np = X; op..sp = O)
    # q . X X O O O O O O   (lq,mq = X; nq..sq = O)
    # r X . O . X X O O O   (kr=X, lr=., mr=O, nr=., or=X, pr=X, qr..sr=O)
    # s X X O . . . O . .   (ks=X, ls=X, ms=O, ns=., os=., ps=., qs=O, rs=., ss=.)
    ab = [
        "mo", "no", "oo", "po", "qo", "ro", "so",
        "lp", "mp", "np",
        "lq", "mq",
        "kr", "or", "pr",
        "ks", "ls",
    ]
    aw = [
        "op", "pp", "qp", "rp", "sp",
        "nq", "oq", "pq", "qq", "rq", "sq",
        "mr", "qr", "rr", "sr",
        "ms", "qs",
    ]
    ab_s = "".join(f"[{s}]" for s in ab)
    aw_s = "".join(f"[{s}]" for s in aw)

    b = sum(1 << sgf_to_pt(s) for s in ab)
    w = sum(1 << sgf_to_pt(s) for s in aw)
    empty_pts = ["lr", "nr", "ns", "os", "ps", "rs", "ss"]
    cap_pts = ["mr", "ms", "or", "pr"]
    combat = sum(1 << sgf_to_pt(s) for s in empty_pts + cap_pts)
    imm_att = b & ~sum(1 << sgf_to_pt(s) for s in ["or", "pr"])
    outside = BOARD_MASK ^ (combat | w)

    spec = TsumegoSpec(
        black=b, white=w, first_player="B", defender="W",
        target_stones=w, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )

    # First let solver verify if 4.W[ps]; 5.B[ns] under 2.W[os]; 3.B[lr] needs 6.W[...]; 7.B[...]!
    sol = TsumegoSolver(spec, max_depth=26)
    cb, cw, ck = b, w, None
    for col, mv in [("B","nr"),("W","os"),("B","lr"),("W","ps"),("B","ns")]:
        cb, cw, ck = play_move(cb, cw, col, sgf_to_pt(mv), ck)
    # After 5.B[ns] (capturing mr, ms), check if W has any threat if B passes:
    w_threats_after_os_ps_ns = []
    for wm, _ in sol.analyze_moves(cb, cw, "W", ck):
        if wm in ("rs", "ss"): continue
        nb2, nw2, nk2 = play_move(cb, cw, "W", sgf_to_pt(wm), ck)
        if sol.evaluate(nb2, nw2, "W", None) != 0:
            w_threats_after_os_ps_ns.append((wm, [m for m,v in sol.analyze_moves(nb2, nw2, "B", nk2) if v == 0]))
    print("Check after 1.B[nr] 2.W[os] 3.B[lr] 4.W[ps] 5.B[ns], W threats:", w_threats_after_os_ps_ns)

    # Also check 1.B[nr] 2.W[lr] winning replies for B:
    b1, w1, k1 = play_move(b, w, "B", sgf_to_pt("nr"))
    b2, w2, k2 = play_move(b1, w1, "W", sgf_to_pt("lr"), k1)
    print("After 1.B[nr] 2.W[lr], B wins:", [m for m,v in sol.analyze_moves(b2, w2, "B", k2) if v == 0])

    # Build complete exact SGF tree:
    # - 1. B[nr] (unique!)
    #   - 2. W[ns] -> 3. B[lr] (unique!)
    #     - 4. W[os] -> 5. B[ps]C[RIGHT]
    #     - 4. W[ps] -> 5. B[os]C[RIGHT]
    #   - 2. W[os] -> 3. B[lr] (unique!)
    #     - 4. W[ns] -> 5. B[ps]C[RIGHT]
    #     - 4. W[ps] -> 5. B[ns] -> (6. W[mr]; 7. B[ms]C[RIGHT]) | (6. W[ms]; 7. B[mr]C[RIGHT])
    #   - 2. W[ps] -> 3. B[lr] (unique!)
    #     - 4. W[ns] -> 5. B[os]C[RIGHT]
    #     - 4. W[os] -> 5. B[ns] -> (6. W[mr]; 7. B[ms]C[RIGHT]) | (6. W[ms]; 7. B[mr]C[RIGHT])
    #   - 2. W[lr] -> (3. B[ns]C[RIGHT]) | (3. B[os]; 4. W[ps]; 5. B[ns]C[RIGHT])
    # - Wrong 1st moves:
    #   - 1. B[lr] -> 2. W[nr]
    #   - 1. B[ns] -> 2. W[nr]
    #   - 1. B[os] -> 2. W[nr]
    #   - 1. B[ps] -> 2. W[nr]
    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;B[nr]"
        f"(;W[ns];B[lr]"
        f"(;W[os];B[ps]C[RIGHT])"
        f"(;W[ps];B[os]C[RIGHT]))"
        f"(;W[os];B[lr]"
        f"(;W[ns];B[ps]C[RIGHT])"
        f"(;W[ps];B[ns](;W[mr];B[ms]C[RIGHT])(;W[ms];B[mr]C[RIGHT])))"
        f"(;W[ps];B[lr]"
        f"(;W[ns];B[os]C[RIGHT])"
        f"(;W[os];B[ns](;W[mr];B[ms]C[RIGHT])(;W[ms];B[mr]C[RIGHT])))"
        ")"
        f"(;B[lr];W[nr])"
        f"(;B[ns];W[nr])"
        f"(;B[os];W[nr])"
        f"(;B[ps];W[nr]))\n"
    )
    return sgf, spec


if __name__ == "__main__":
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
