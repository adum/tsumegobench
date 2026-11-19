#!/usr/bin/env python3
"""Engineer a 7-to-9 forced-move 1-2 dan top-left stepped masterpiece for outputs/problem-10.sgf!"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_dan import eval_dan

if __name__ == "__main__":
    # All candidates use a stepped L-shape in the top-left corner (cols a..i, rows a..g) — NOT a flat rectangle!
    # Left leg (rows d..g, cols a..c) holds White's 1st eye `{af, ag}`.

    # Circuit 1: `db=X, eb=X` + `fa=X` on 1st line, `gb=.`, `ha=.`, `ia=X`!
    eval_dan("Dan10-C1", [
        "...O.X..X",  # a(0): aa,ba,ca=.; da=O? No: ca=., da=., ea=., fa=X, ga=., ha=., ia=X!
    ][:0] + [
        ",O...X..X",  # a(0): ba=O; ca,da,ea=.; fa=X; ga,ha=.; ia=X
        "OOOXXO.XX",  # b(1): ab..cb=O; db,eb=X; fb=O, gb=.; hb,ib=X
        "XXOOOOOXX",  # c(2): ac,bc=X; cc..gc=O; hc,ic=X? Wait left leg needs to connect! Make ac,bc=O!
    ][:0] + [
        # Connect left leg cleanly down col a..c, rows a..f:
        "XO...X..X",  # a(0): aa=X? Put eye {ae,af} at bottom of left leg!
        # Let's draw rows a(0)..f(5), cols a(0)..h(7):
        #   a b c d e f g h
        # a X X O . . X . X   (aa,ba=X; ca=O; da,ea=.; fa=X, ga=., ha=X)
        # b X O O X X O . X   (ab=X; bb,cb=O; db,eb=X; fb=O, gb=., hb=X)
        # c O O O O . O O X   (ac..dc=O, ec=., fc,gc=O, hc=X)
        # d . O X X O O X X   (ad=., bd=O; cd,dd=X; ed,fd=O; gd,hd=X)
        # e . O X , , X X ,   (ae=., be=O, ce=X) -> {ad, ae} = 2-pt single eye when af=O!
        # f O O X , , , , ,   (af,bf=O, cf=X) -> connect aa,ba,ab outside? aa,ba,ab only has 0 libs!
        # Put {aa, ab} as White's corner 2-pt eye, and step DOWN on the right (`e..h, c..f`) so shape is an L/boot!
    ] + [
        ".O...X.X,",  # a(0): aa=., ba=O; ca,da,ea=.; fa=X, ga=., ha=X
        ".OOXXO.X,",  # b(1): ab=.; bb,cb=O; db,eb=X; fb=O, gb=., hb=X
        "OOOO.OOX,",  # c(2): ac..dc=O, ec=., fc,gc=O, hc=X
        "XXXXO.OX,",  # d(3): ad..dd=X, ed=O, fd=., gd=O, hd=X
        ",,,,XOOX,",  # e(4): ee=X; fe,ge=O; he=X
        ",,,,,XX,,",  # f(5): fe,ge enclosed by ff,gf=X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fa"], ignore_pts={"aa", "ab"})

    # Circuit 2: Give `fa=X` stone `ga=X` (`fa,ga=X`, `ha=.`, `ia=X`) so `fa-ga` has 2 liberties `ea` and `ha`!
    eval_dan("Dan10-C2", [
        ".O...XX.X",  # a(0): aa=., ba=O; ca,da,ea=.; fa,ga=X, ha=., ia=X
        ".OOXXOO.X",  # b(1): ab=.; bb,cb=O; db,eb=X; fb,gb=O, hb=., ib=X
        "OOOO.OOOX",  # c(2): ac..dc=O, ec=., fc..hc=O, ic=X
        "XXXXOOXXX",  # d(3): ad..dd=X; ed,fd=O; gd..id=X
        ",,,,XX,,,",  # e(4): ee,fe = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fa", "ga"], ignore_pts={"aa", "ab"})

    # Circuit 3: `ec = O` ALREADY connected, and instead on the right `hc = .` (`fc,gc=O` needs to connect OR squeeze `db-eb` + `fa-ga`!):
    eval_dan("Dan10-C3", [
        ".O...XX.X",  # a(0): aa=., ba=O; ca,da,ea=.; fa,ga=X, ha=., ia=X
        ".OOXXOO.X",  # b(1): ab=.; bb,cb=O; db,eb=X; fb,gb=O, hb=., ib=X
        "OOOOOO.XX",  # c(2): ac..fc=O, gc=., hc,ic=X
        "XXXXXOXX,",  # d(3): ad..ed=X, fd=O, gd,hd=X
        ",,,,,X,,,",  # e(4): fe=X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fa", "ga", "fb", "gb"], ignore_pts={"aa", "ab"})

    # Circuit 4: White to KILL in top-left (`a..i, a..f`) via 7-to-9 move under-the-stones / throw-in squeeze!
    # Take our proven 7-move P09 (`1.B[nb] -> 2.W[ma] -> ...`), DO NOT mirror it — instead build a **9-move** version where an EXTRA preliminary 1st-line probe is required!
    # Look! Why did P09 take 7 moves? `1.W[nb] -> 2.B[ma] -> 3.W[la] -> 4.B[pa] -> 5.W[oa] -> 6.B[mb] -> 7.W[ma]`.
    # What if `ka` (which was already on the board in P09!) is NOT connected yet — instead `ja=O, ka=.`? No, if `ka=.` then `3.W[la]` needs `1.W[ka]` first? If `1.W[ka]`, `2.B[nb]` lives!
    # What if on the OTHER side (`pa, qa`), White has a sente throw-in `1.W[ra] -> 2.B[qa]` BEFORE `3.W[nb]` -> **9 FORCED MOVES**!!
    # TEST THAT!! In P09 (flipped colors AND altered geometry with a bottom boot so it's a totally different problem AND 9 forced moves!):
    # Suppose Black's right wing does NOT already have `{ra, sa}` — instead Black has `{sa}` (1 eye) PLUS a tiger's mouth at `qa` (`pa=X, qa=., ra=X`, with `qb=.`?!):
    eval_dan("Dan10-9move-kill-A", [
        "O..X..X..",  # a(0): aa=O; ba,ca=.; da=X; ea,fa=.; ga=X; ha,ia=.
        "OOX.OOXXX",  # b(1): ab,bb=O; cb=X, db=.; eb,fb=O; gb..ib=X
        ",OOXXXXXO",  # c(2): bc,cc=O; dc..hc=X; ic=O
        ",,,OOXOOO",  # d(3): dd,ed=O; fd=X; gd..id=O  <-- bottom boot!
        ",,,,OOO,,",  # e(4): ee..ge=O
    ], r0=0, c0=0, first="W", defender="B", cap_coords=["da", "cb", "eb", "fb", "fd"], ignore_pts={"ha", "ia"})

    # Circuit 5: Add a 2-move probe on the bottom boot (`fd=., gd=X, fe=.`) so White MUST probe the boot (`1.W[fe] -> 2.B[fd]`) BEFORE `3.W[db]` -> **9 FORCED MOVES**!!
    eval_dan("Dan10-9move-kill-B", [
        "O..X..X..",  # a(0): aa=O; ba,ca=.; da=X; ea,fa=.; ga=X; ha,ia=.
        "OOX.OOXXX",  # b(1): ab,bb=O; cb=X, db=.; eb,fb=O; gb..ib=X
        ",OOXX.XXO",  # c(2): bc,cc=O; dc,ec=X, fc=., gc,hc=X, ic=O  <-- potential eye {fc} unless probed!
        ",,,OX.XOO",  # d(3): dd=O, ed=X, fd=., gd=X; hd,id=O
        ",,,,O.O,,",  # e(4): ee=O, fe=., ge=O
        ",,,,,O,,,",  # f(5): ff=O
    ], r0=0, c0=0, first="W", defender="B", cap_coords=["da", "cb", "eb", "fb"], ignore_pts={"ha", "ia"})
