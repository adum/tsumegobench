#!/usr/bin/env python3
"""Verify clean P07 (1-4k B kill, bottom-right) and design 7-move P08 (1-4k W live, top-left)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_p07_p08 import analyze_deep

if __name__ == "__main__":
    print("=== P07 Clean Border Check ===")
    analyze_deep("P07-clean", [
        ",,,,,,XX",  # n(13): rn=X, sn=X
        ",XXXXXX.",  # o(14): mo..ro=X, so=. (natural 1st-line dame liberty for W!)
        "XXXOOOOO",  # p(15): lp,mp,np=X; op..sp=O
        "XXOOOOOO",  # q(16): lq,mq=X; nq..sq=O
        "XO.XXOOO",  # r(17): lr=X, mr=O, nr=., or=X, pr=X, qr=O, rr=O, sr=O
        "XO...OO.",  # s(18): ls=X, ms=O, ns=., os=., ps=., qs=O, rs=O, ss=.
    ], r0=13, c0=11, first="B", defender="W", cap_coords=["mr", "ms", "or", "pr"])

    print("\n=== P08 7-Move Probe + Live Candidates (1-4 kyu, White to play and live) ===")
    # Take our 5-move miai-junction concept or false-eye-trap concept and couple it with a mandatory sente probe!
    # Look at top-left / left side (cols a..f, rows b..k):
    # Suppose White has a group on the left edge (cols a..d, rows c..j):
    # - Top wing: 3-space `{ad, ae, af}`? Wait: in P04, `1.W[rg]` was 5 moves!
    #   Why not build a COMPLETELY DIFFERENT tactical mechanism for P08:
    #   **Throw-in Squeeze (`oiotoshi` / shortage of liberties) to Capture a Cutting Stone & Make Two Eyes in 7 Moves**!
    #   Let's trace!
    #   White's group in top-left (`a..h, a..e`) has 1 eye at `{aa}` (`ba=O, ab=O, bb=O` -> `{aa}` is 1 eye!).
    #   To the right (`c..h`), Black has TWO cutting stones `db=X, eb=X` (with `da=., ea=.` above them!) separating `ba-bb-cb-cc` from `fb=O, fc=O`!
    #   If White plays `1. W[fa]` (1st-line hane!) -> `2. B[ea]` (extends to 3 stones `db-eb-ea`?):
    #   Wait: trace how White squeezes `db-eb` on the 1st line (`1.W[fa] -> 2.B[da] -> 3.W[ea] throw-in -> 4.B[fa]?`!):
    #   YES!! **1ST-LINE THROW-IN SQUEEZE (`1. W[ga] -> 2. B[fa] -> 3. W[da] -> ...`)**!
    #   Let's test 4 distinct 7-move top-left White-to-live constructions!
    analyze_deep("P08-cand1 (squeeze on top-left)", [
        ".O...OXX,",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=O, ga=X, ha=X
        "OOOXO.XX,",  # b(1): ab=O, bb=O, cb=O, db=X, eb=O, fb=., gb=X, hb=X
        "XXXOOOXX,",  # c(2): ac,bc,cc=X; dc,ec,fc=O; gc,hc=X
        ",,,XXXX,,",  # d(3): dd..gd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "fa", "eb"])

    analyze_deep("P08-cand2 (double hane + throw-in)", [
        ".O....XX,",  # a(0): aa=., ba=O, ca=., da=., ea=., fa=., ga=X, ha=X
        "OOOXOOXX,",  # b(1): ab=O, bb=O, cb=O, db=X, eb=O, fb=O, gb=X, hb=X
        "XXXO.OXX,",  # c(2): ac,bc,cc=X; dc=O, ec=., fc=O; gc,hc=X
        ",,,XXXX,,",  # d(3): dd..gd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb", "fb", "fc"])

    analyze_deep("P08-cand3 (1st-line clamp + throw-in)", [
        ".OO...XX,",  # a(0): aa=., ba=O, ca=O, da=., ea=., fa=., ga=X, ha=X
        "OO.XO.XX,",  # b(1): ab=O, bb=O, cb=., db=X, eb=O, fb=., gb=X, hb=X
        "XXOOOXXX,",  # c(2): ac,bc=X; cc,dc,ec=O; fc,gc,hc=X
        ",,XXXX,,,",  # d(3): cd..fd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "eb"])

    analyze_deep("P08-cand4 (sacrifice + snapback eye)", [
        ".O..O.XX,",  # a(0): aa=., ba=O, ca=., da=., ea=O, fa=., ga=X, ha=X
        "OO.XO.XX,",  # b(1): ab=O, bb=O, cb=., db=X, eb=O, fb=., gb=X, hb=X
        "XXOO.OXX,",  # c(2): ac,bc=X; cc,dc=O; ec=.; fc=O; gc,hc=X
        ",,XXXXX,,",  # d(3): cd..gd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["db", "ea", "eb", "fc"])
