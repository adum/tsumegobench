#!/usr/bin/env python3
"""
1. Verify and originality-check outputs/problem-08.sgf (1-4 kyu, White to live via 2-stone bait sacrifice + directional semeai, right-lower side o..s, g..n).
2. Search 7-11 move 1-2 dan candidates in top-left corner (a..h, a..g) for outputs/problem-10.sgf!
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, play_move, sgf_to_pt, validate_sgf_candidate
from tree_verifier import verify_tree_against_solver
from originality_client import query_originality
from make_p08 import auto_build_right_subtree
from search_dan import eval_dan

ROOT = Path(__file__).resolve().parent.parent


def build_p08_fresh() -> tuple[str, TsumegoSpec]:
    # Mirror/place tall stepped bait-sacrifice semeai on lower-right side (cols o..s, rows g..n), 31 setup stones:
    # (Flipping col a->s, b->r, c->q, d->p, e->o; rows g(6)..n(13), compact 1-row-shorter bottom eye {sm, sn}!)
    #   o p q r s
    # g . X X X X   (pg..sg = X)
    # h . X X . X   (ph,qh=X, rh=., sh=X)
    # i X X . . O   (oi,pi=X; qi,ri=.; si=O)
    # j X O O X .   (oj=X; pj,qj=O; rj=X, sj=.)
    # k X O O X X   (ok=X; pk,qk=O; rk,sk=X)
    # l X X O O .   (ol,pl=X; ql,rl=O; sl=.)
    # m X X O O O   (om,pm=X; qm..sm=O)
    # n . X O O .   (pn=X; qn,rn=O; sn=.)  <-- {sn} is 1 real eye if so=O! Better: {rn, sn}?
    # Let's use the exact 2-pt single eye `{sn, so}` (`qm..sm=O, qn,rn=O, qo,ro=O` — zero extra Black stones needed below!):
    #   o p q r s
    # f . X X X X   (pf..sf = X)
    # g . X X . X   (pg,qh? pg,qg=X, rg=., sg=X)
    # h X X . . O   (oh,ph=X; qh,rh=.; sh=O)
    # i X O O X .   (oi=X; pi,qi=O; ri=X, si=.)
    # j X O O X X   (oj=X; pj,qj=O; rj,sj=X)
    # k X X O O .   (ok,pk=X; qk,rk=O; sk=.)
    # l X X O O O   (ol,pl=X; ql..sl=O)
    # m . X O O .   (pm=X; qm,rm=O; sm=.)
    # n . X O O .   (pn=X; qn,rn=O; sn=.)
    # o . . X X X   (qo..so = X? Wait if so=X then sn touches X! Keep {sm,sn} enclosed by O: ro,so=O, po,qo,rp,sp=X? No: put {sm} at row m, so=O? Just go down to row s = board bottom edge so row s closes {sr, ss} naturally with ZERO bottom stones!!)
    # YES!! Ending at row s (bottom edge!) closes `{sr, ss}` naturally with ZERO extra wall stones!
    # Rows k(10)..s(18), cols o(14)..s(18):
    grid = [
        ",XXXX",  # k(10): pk..sk = X
        ",XX.X",  # l(11): pl,ql=X, rl=., sl=X
        "XX..O",  # m(12): om,pm=X; qm,rm=.; sm=O
        "XOOX.",  # n(13): on=X; pn,qn=O; rn=X, sn=.
        "XOOXX",  # o(14): oo=X; po,qo=O; ro,so=X
        "XXOO.",  # p(15): op,pp=X; qp,rp=O; sp=.
        "XXOOO",  # q(16): oq,pq=X; qq..sq=O
        ",XOO.",  # r(17): pr=X; qr,rr=O; sr=.
        ",XOO.",  # s(18): ps=X; qs,rs=O; ss=.   ({sr,ss} = 2-pt single eye in corner!)
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
    sol = TsumegoSolver(spec, max_depth=26)

    # Winning first move: 1. W[rm] (2-stone bait sacrifice!)
    b1, w1, k1 = play_move(b, w, "W", sgf_to_pt("rm"))
    right_tail = auto_build_right_subtree(sol, b1, w1, k1, "W", 4, {"sr", "ss"}, depth=1)

    # Wrong first moves (and also include wrong 3.W[sn] under 1.W[rm]; 2.B[qm] to highlight the directional trap!):
    # Wait: let's inject `(;W[sn];B[rl])` under `;B[qm]` inside `right_tail`!
    wrong_branches = []
    for wm in ["qm", "sn", "sp", "rl"]:
        wb, ww, wk = play_move(b, w, "W", sgf_to_pt(wm))
        breps = [m for m, v in sol.analyze_moves(wb, ww, "B", wk) if v < 4 and m not in ("sr", "ss")]
        best_b = breps[0]
        print(f"P08 wrong 1.W[{wm}] -> 2.B[{best_b}]")
        wrong_branches.append(f"(;W[{wm}];B[{best_b}])")

    # Add the instructive wrong 3rd move `(;W[sn];B[rl])` under `(;B[qm];W[sp]...`!
    assert "(;B[qm];W[sp]" in right_tail, right_tail
    right_tail = right_tail.replace("(;B[qm];W[sp]", "(;B[qm](;W[sp]")
    # Close the extra paren at the end of the B[qm] branch:
    idx_qm = right_tail.index("(;B[qm](;W[sp]")
    # Find matching ')' of `(;B[qm]`!
    depth_p = 0
    end_qm = -1
    for i in range(idx_qm, len(right_tail)):
        if right_tail[i] == "(":
            depth_p += 1
        elif right_tail[i] == ")":
            depth_p -= 1
            if depth_p == 0:
                end_qm = i
                break
    right_tail = right_tail[:end_qm] + ")(;W[sn];B[rl]))" + right_tail[end_qm + 1:]

    sgf = (
        f"(;FF[4]GM[1]CA[UTF-8]SZ[19]AB{ab_s}AW{aw_s}"
        f"(;W[rm]{right_tail})"
        f"{''.join(wrong_branches)})\n"
    )
    return sgf, spec


if __name__ == "__main__":
    print("=== Verifying & Checking Originality of Fresh P08 ===")
    sgf8, spec8 = build_p08_fresh()
    print("P08 SGF:", sgf8.strip())
    ok8, errs8, notes8 = verify_tree_against_solver(sgf8, spec8, max_depth=26)
    print("P08 tree verification:", ok8, errs8)
    for n in notes8:
        print(" ", n)
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

    print("\n=== Searching 7-9 Move 1-2 Dan Top-Left Candidates for P10 (White to play) ===")
    # Top-left corner/skirt (cols a..i, rows a..f) — stepped non-rectangular shape!
    # Candidate 10-1: White to KILL Black in top-left via 7-9 move clamp + throw-in + under-the-stones!
    eval_dan("P10-TL-kill-1", [
        "..X..X..O",  # a(0): aa,ba=.; ca=X; da,ea=.; fa=X; ga,ha=.; ia=O
        "XXXOOXXOO",  # b(1): ab..cb=X; db,eb=O; fb,gb=X; hb,ib=O
        "OOOO.XXO,",  # c(2): ac..dc=O, ec=.; fc,gc=X; hc=O
        ",,,OOXOO,",  # d(3): dd,ed=O, fd=X; gd,hd=O
        ",,,,OOO,,",  # e(4): ee..ge = O
    ], r0=0, c0=0, first="W", defender="B", cap_coords=["db", "eb", "fa", "fb", "gb", "fc", "gc", "fd"][:2], ignore_pts={"aa", "ba"})

    # Keep cap_coords small (<=4) so <0.1s!
    # Look: in P10-TL-kill-2, Black has `{aa, ba}` 2-pt eye, and on right (`c..h, a..d`) White has `eb=O` inside and kills in 7-9 moves!
    eval_dan("P10-TL-kill-2", [
        "..X..X..O",  # a(0): aa,ba=.; ca=X; da,ea=.; fa=X; ga,ha=.; ia=O
        "XXX.OOXXO",  # b(1): ab..cb=X, db=.; eb,fb=O; gb,hb=X; ib=O
        "OOOXXXOO,",  # c(2): ac..cc=O; dc..fc=X; gc,hc=O
        ",,OOOOO,,",  # d(3): cd..gd = O
    ], r0=0, c0=0, first="W", defender="B", cap_coords=["eb", "fb", "gb", "hb"], ignore_pts={"aa", "ba"})

    # Candidate 10-3: Stepped top-left White-to-LIVE in 7-9 moves (2-stage probe + 5-move sequence)!
    eval_dan("P10-TL-live-3", [
        "..O..O..X",  # a(0): aa,ba=.; ca=O; da,ea=.; fa=O; ga,ha=.; ia=X
        "OOO.XXOOX",  # b(1): ab..cb=O, db=.; eb,fb=X; gb,hb=O; ib=X
        "XXXOOOXX,",  # c(2): ac..cc=X; dc..fc=O; gc,hc=X
        ",,XXXXX,,",  # d(3): cd..gd = X  <-- break rectangle on row c/d with stepped right leg!
    ][:2] + [
        "XXOOOO.XX",  # c(2): ac,bc=X; cc..fc=O, gc=.; hc,ic=X
        ",,XXXXOXX",  # d(3): cd..fd=X, gd=O, hd,id=X
        ",,,,,XXX,",  # e(4): fe..he = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["eb", "fb", "fa", "gb", "hb", "gd"][:4], ignore_pts={"aa", "ba"})
