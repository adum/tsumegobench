#!/usr/bin/env python3
"""
Search & verify genuine 7-to-11 move problems for:
- problem-08 (1-4 kyu, White to play and LIVE, top-left corner/side)
- problem-09 (about 1 dan, Black to play and KILL, upper-right corner/side)
- problem-10 (about 1-2 dan, White to play and LIVE, bottom-left/side or right-corner)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from go_engine import BOARD_MASK, TsumegoSolver, TsumegoSpec, iter_components, opp_color, play_move, sgf_to_pt


def forced_depth_and_tree(spec: TsumegoSpec, sol: TsumegoSolver, b: int, w: int, ko: int | None, side: str, target_v: int, ignore_pts: set[str], d: int = 0) -> int:
    """
    Exact forced minimax depth until settled (protagonist could pass/tenuki against all opponent tries).
    """
    prot = spec.first_player
    ant = opp_color(prot)
    if d >= 13:
        return d

    if side == ant and d > 0:
        # Check if ant has ANY move `am` after which prot passing (`ant` moves again!) breaks `target_v`!
        real_threats = []
        for am, _ in sol.analyze_moves(b, w, ant, ko):
            if am in ignore_pts:
                continue
            nb, nw, nko = play_move(b, w, ant, sgf_to_pt(am), ko)
            if sol.evaluate(nb, nw, ant, None) != target_v:
                real_threats.append((am, nb, nw, nko))
        if not real_threats:
            return d
        return max(
            forced_depth_and_tree(spec, sol, nb, nw, nko, prot, target_v, ignore_pts, d + 1)
            for _, nb, nw, nko in real_threats[:4]
        )

    # side == prot
    mvs = [(m, v) for m, v in sol.analyze_moves(b, w, prot, ko) if v == target_v and m not in ignore_pts]
    if not mvs:
        return d
    return min(
        forced_depth_and_tree(spec, sol, *play_move(b, w, prot, sgf_to_pt(m), ko)[:2], play_move(b, w, prot, sgf_to_pt(m), ko)[2], ant, target_v, ignore_pts, d + 1)
        for m, _ in mvs[:3]
    )


def eval_dan(name: str, grid: list[str], r0: int, c0: int, first: str, defender: str, cap_coords: list[str], ignore_pts: set[str] = frozenset()):
    b = w = ec = 0
    for dr, row_s in enumerate(grid):
        row = row_s.replace(" ", "")
        for dc, ch in enumerate(row):
            pt = (r0 + dr) * 19 + (c0 + dc)
            if ch == "X":
                b |= 1 << pt
            elif ch == "O":
                w |= 1 << pt
            elif ch == ".":
                ec |= 1 << pt
    def_stones = b if defender == "B" else w
    att_stones = w if defender == "B" else b
    cap = sum(1 << sgf_to_pt(s) for s in cap_coords)
    imm_att = att_stones & ~cap
    combat = ec | cap
    outside = BOARD_MASK ^ (ec | cap | def_stones)

    spec = TsumegoSpec(
        black=b, white=w, first_player=first, defender=defender,
        target_stones=def_stones, combat_mask=combat,
        outside_mask=outside, immortal_attacker=imm_att,
    )
    sol = TsumegoSolver(spec, max_depth=28)
    opp = opp_color(first)
    opp_v = sol.evaluate(b, w, opp)
    mvs = [(m, v) for m, v in sol.analyze_moves(b, w, first) if m not in ignore_pts]
    if not mvs:
        return
    bv = mvs[0][1]
    wins = [m for m, v in mvs if v == bv]
    fdepth = forced_depth_and_tree(spec, sol, b, w, None, first, bv, ignore_pts, 0) if (len(wins) == 1 and opp_v != bv) else -1
    print(f"{name:28s}: stones={(b|w).bit_count():2d} opp1st={TsumegoSolver.OUTCOME_NAMES[opp_v]:10s} best={TsumegoSolver.OUTCOME_NAMES[bv]:10s} wins={wins} forced_ply={fdepth}")
    print(f"   all 1st: {[(m, TsumegoSolver.OUTCOME_NAMES[v]) for m,v in mvs]}")
    if len(wins) == 1 and fdepth >= 5:
        m1 = wins[0]
        b1, w1, k1 = play_move(b, w, first, sgf_to_pt(m1))
        for m2, v2 in sol.analyze_moves(b1, w1, opp, k1):
            if m2 in ignore_pts: continue
            b2, w2, k2 = play_move(b1, w1, opp, sgf_to_pt(m2), k1)
            if sol.evaluate(b2, w2, opp, None) != bv:
                w3 = [m for m, v in sol.analyze_moves(b2, w2, first, k2) if v == bv and m not in ignore_pts]
                print(f"   1.{first}[{m1}] -> 2.{opp}[{m2}] -> 3.{first}: {w3}")
                for m3 in w3[:2]:
                    b3, w3b, k3 = play_move(b2, w2, first, sgf_to_pt(m3), k2)
                    for m4, _ in sol.analyze_moves(b3, w3b, opp, k3):
                        if m4 in ignore_pts: continue
                        b4, w4, k4 = play_move(b3, w3b, opp, sgf_to_pt(m4), k3)
                        if sol.evaluate(b4, w4, opp, None) != bv:
                            w5 = [m for m, v in sol.analyze_moves(b4, w4, first, k4) if v == bv and m not in ignore_pts]
                            print(f"      3.{first}[{m3}] -> 4.{opp}[{m4}] -> 5.{first}: {w5}")
                            for m5 in w5[:2]:
                                b5, w5b, k5 = play_move(b4, w4, first, sgf_to_pt(m5), k4)
                                for m6, _ in sol.analyze_moves(b5, w5b, opp, k5):
                                    if m6 in ignore_pts: continue
                                    b6, w6, k6 = play_move(b5, w5b, opp, sgf_to_pt(m6), k5)
                                    if sol.evaluate(b6, w6, opp, None) != bv:
                                        w7 = [m for m, v in sol.analyze_moves(b6, w6, first, k6) if v == bv and m not in ignore_pts]
                                        print(f"         5.{first}[{m5}] -> 6.{opp}[{m6}] -> 7.{first}: {w7}")


if __name__ == "__main__":
    print("=== P08: Top-Left White to LIVE (target 7+ ply, 1-3 kyu) ===")
    # Idea A: Throw-in squeeze on 2 Black cutting stones to connect & form 2nd eye!
    # Give right White block 3 liberties (`fa, ga, ha`? No: `fa, ga` + eye/connection!)
    eval_dan("P08-A (throw-in squeeze live)", [
        "..O....XX",  # a(0): aa=., ba=., ca=O, da=., ea=., fa=., ga=., ha=X, ia=X (aa,ba = 2-pt single eye!)
        "OOOXXOOXX",  # b(1): ab..cb=O; db,eb=X; fb,gb=O; hb,ib=X
        "XXXO.OOXX",  # c(2): ac..cc=X; dc=O, ec=., fc,gc=O; hc,ic=X
        ",,,XXXXX,",  # d(3): dd..hd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "dc", "fc", "gc", "fb", "gb"], ignore_pts={"aa", "ba"})

    # Wait: in P08-A, why did `db-eb` survive earlier? Because `dc` was next to `db` (`dc` only had `ec`!).
    # Make `dc = X`? No, if `dc = O` is ALREADY connected (`cc=O`!!), so ONLY `fb-gb` is cut off by `db-eb-ec`?!
    # TRACE THAT!!
    # Left White (`ba, ab, bb, cb, cc, dc`) ALREADY has 1 eye `{aa}` AND is ONE solid chain!
    # Right White (`fb, gb, gc`) has liberties `fa, ga` AND `fc`!
    # Cutting Black stones: `db=X, eb=X, ec=X` (`3` Black stones cutting Left White from Right White, with liberties `da, ea, fc`!!)!
    eval_dan("P08-B (squeeze 3 cutting stones)", [
        ".O.....XX",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=., ha=X, ia=X
        "OOOXXOOXX",  # b(1): ab..cb=O; db,eb=X; fb,gb=O; hb,ib=X
        "XXOOX.OXX",  # c(2): ac,bc=X; cc,dc=O; ec=X; fc=.; gc=O; hc,ic=X
        ",,XXXXXX,",  # d(3): cd..hd = X (WAIT: ec=X touches ed=X?! Make ed=O so db-eb-ec is CUT OFF from Black's outer wall!!)
    ][:3] + [
        ",,XOOOXX,",  # d(3): cd=X; dd,ed,fd=O; gd,hd=X
        ",,,XXXX,,",  # e(4): de..ge = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "ec", "fb", "gb", "gc"], ignore_pts={"aa"})

    eval_dan("P08-C (squeeze 2 cutting stones)", [
        ".O....XX,",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=X, ha=X
        "OOOXXOXX,",  # b(1): ab..cb=O; db,eb=X; fb=O; gb,hb=X
        "XXOO.OXX,",  # c(2): ac,bc=X; cc,dc=O; ec=.; fc=O; gc,hc=X
        ",,XOOOXX,",  # d(3): cd=X; dd,ed,fd=O; gd,hd=X  <-- bottom connected via dd-ed-fd!
        ",,,XXXX,,",  # e(4): de..ge = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb"], ignore_pts={"aa"})

    # What if `fb` is NOT connected via `fd=O` (`fd=X`), instead `fb-fc` has 1 eye/lib? Let's test `fd=X` (`dd,ed=O`, `ec=.`)!
    eval_dan("P08-D (oiotoshi squeeze)", [
        ".O.....XX",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=., ha=X, ia=X
        "OOOXXOOXX",  # b(1): ab..cb=O; db,eb=X; fb,gb=O; hb,ib=X
        "XXOO.OOXX",  # c(2): ac,bc=X; cc,dc=O; ec=.; fc,gc=O; hc,ic=X
        ",,XXOXXX,",  # d(3): cd,dd=X; ed=O?; fd..hd=X -> keep dd,ed=X:
    ][:3] + [
        ",,XXXXXX,",  # d(3): cd..hd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fb", "gb", "fc", "gc"], ignore_pts={"aa"})

    print("\n=== P09: Upper-Right 1-Dan Black to KILL (target 7-11 ply, clamp + throw-in / under-the-stones) ===")
    # Inspired by 1-dan corner/edge tactical richness (non-contact placement / clamp + multi-step throw-in avoiding ko/seki!)
    # Upper-right corner: cols l(11)..s(18), rows a(0)..e(4)
    eval_dan("P09-A (1d corner clamp + throw-in)", [
        ",X..O...",  # a(0): ma=X, na=., oa=., pa=O, qa=., ra=., sa=.
        ",XXOO.OO",  # b(1): mb,nb=X; ob,pb=O; qb=.; rb,sb=O
        ",,XXOOOX",  # c(2): nc,oc=X; pc,qc,rc=O; sc=X
        ",,,,XXXX",  # d(3): pd..sd = X
    ], r0=0, c0=11, first="B", defender="W", cap_coords=["pa", "ob", "pb", "rb", "sb"])

    eval_dan("P09-B (1d 3-stone under-the-stones kill)", [
        "X...O..O",  # a(0): la=X, ma=., na=., oa=., pa=O, qa=., ra=., sa=O
        "XOXXOOOO",  # b(1): lb=X, mb=O, nb=X, ob=X, pb=O, qb=O, rb=O, sb=O
        "XOOOOOOX",  # c(2): lc=X, mc..rc=O, sc=X  <-- wait mb-mc..rc is ALL connected! Make mc=X so mb is jaw!
    ][:2] + [
        "XXOOOO.X",  # c(2): lc,mc=X; nc..qc=O; rc=.; sc=X (rc=. gives W outside lib!)
        ",,XXXXXX",  # d(3): nd..sd = X
    ], r0=0, c0=11, first="B", defender="W", cap_coords=["mb", "nb", "ob"], ignore_pts={"rc"})

    eval_dan("P09-C (1d sacrifice + nakade kill)", [
        ",X...O..",  # a(0): ma=X, na=., oa=., pa=., qa=O, ra=., sa=.
        ",XOXXOOO",  # b(1): mb=X, nb=O, ob=X, pb=X, qb=O, rb=O, sb=O
        ",,XXOO.X",  # c(2): nc,oc=X; pc,qc=O; rc=.; sc=X? Wait ob=X touches oc=X! Make oc=O so ob-pb is isolated!
    ][:2] + [
        ",XXOOO.X",  # c(2): mb,nc=X; oc,pc,qc=O; rc=.; sc=X
        ",,,XXXXX",  # d(3): od..sd = X
    ], r0=0, c0=11, first="B", defender="W", cap_coords=["nb", "ob", "pb"], ignore_pts={"rc"})
