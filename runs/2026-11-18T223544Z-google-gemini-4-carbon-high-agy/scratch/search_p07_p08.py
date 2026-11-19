#!/usr/bin/env python3
"""Search 7-9 move 1-4 kyu candidates for P07 (B kill, bottom-right) and P08 (W live, top-left)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_p07_p08 import analyze_deep

if __name__ == "__main__":
    print("=== P07: Bottom-Right 7-9 move Kill (1-4 kyu, Black to play) ===")
    # Fix {ss} eye in P07-ishi-B so White's main group has plenty of liberties and 1 real eye {ss}!
    #   o(14): , X X X X X X X   (mo..so = X)
    #   p(15): X X X O O O O O   (lp,mp,np=X; op..sp=O)
    #   q(16): X O X O O O X O   (lq=X, mq=O, nq=X, oq,pq,qq=O, rq=X? No: oq..sq=O!)
    #   r(17): X O . . X O O O   (lr=X, mr=O, nr=., or=., pr=X, qr=O, rr=O, sr=O)
    #   s(18): X . . . X O O .   (ls=X, ms=., ns=., os=., ps=X, qs=O, rs=O, ss=.) -> {ss} is 1 real eye!
    analyze_deep("P07-ishi-fixed1", [
        ",XXXXXXX",  # o(14): mo..so = X
        "XXXOOOOO",  # p(15): lp,mp,np=X; op..sp=O
        "XOXOOOOO",  # q(16): lq=X, mq=O, nq=X, oq..sq=O
        "XO..XOOO",  # r(17): lr=X, mr=O, nr=., or=., pr=X, qr=O, rr=O, sr=O
        "X...XOO.",  # s(18): ls=X, ms=., ns=., os=., ps=X, qs=O, rs=O, ss=.
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mq", "mr", "pr", "ps"])

    # Variant 2: pr=X alone (ps=.), so B builds the 3-stone sacrifice {or, pr, ps} or {ns, os, or}!
    analyze_deep("P07-ishi-fixed2", [
        ",XXXXXXX",  # o(14)
        "XXXOOOOO",  # p(15)
        "XOXOOOOO",  # q(16)
        "XO..XOOO",  # r(17): lr=X, mr=O, nr=., or=., pr=X, qr=O, rr=O, sr=O
        "X....OO.",  # s(18): ls=X, ms=., ns=., os=., ps=., qs=O, rs=O, ss=.
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mq", "mr", "pr"])

    # Variant 3: Look at canonical gp-16482 / gp-20284 mechanism on 1st/2nd line (flipped/redesigned with asymmetric eye):
    # White has 1 real eye {ss}, and on the left has isolated jaw `mr=O, ms=O`? If `ms=O`, then `nr, ns, or, os`:
    # When B has `or=X, pr=X` (`oq=O, pq=O, qr=O`), `ns=.`, `os=.`, `ps=.`, `nr=.`:
    analyze_deep("P07-ishi-fixed3", [
        ",XXXXXXX",  # o(14)
        "XXXOOOOO",  # p(15)
        "XXOOOOOO",  # q(16): lq,mq=X; nq..sq=O
        "XO.XXOOO",  # r(17): lr=X, mr=O, nr=., or=X, pr=X, qr=O, rr=O, sr=O
        "XO...OO.",  # s(18): ls=X, ms=O, ns=., os=., ps=., qs=O, rs=O, ss=.
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mr", "ms", "or", "pr"])

    # Variant 4: Give `mr-ms` 1 more stone `nq=O`? No, if `nq=O` it connects to `oq=O`!
    # In fixed3, `mr=O, ms=O` has liberties `nr` and `ns`! And `or-pr` has liberties `nr, os, ps`!
    # Also test with `or=.` and `pr=X`:
    analyze_deep("P07-ishi-fixed4", [
        ",XXXXXXX",  # o(14)
        "XXXOOOOO",  # p(15)
        "XXOOOOOO",  # q(16)
        "XO..XOOO",  # r(17): mr=O, nr=., or=., pr=X
        "XO...OO.",  # s(18): ms=O, ns=., os=., ps=.
    ], r0=14, c0=11, first="B", defender="W", cap_coords=["mr", "ms", "pr"])

    print("\n=== P08: Top-Left 7-9 move Live (1-4 kyu, White to play) ===")
    # Probe on right wing + 1st-line hane on left wing!
    analyze_deep("P08-probe-1", [
        "..O..OX.X",  # a(0): aa=., ba=., ca=O, da=., ea=., fa=O, ga=X, ha=., ia=X
        "XO.OO.OXX",  # b(1): ab=X, bb=O, cb=., db=O, eb=O, fb=., gb=O, hb=X, ib=X
        "XXOOXXOXX",  # c(2): ac,bc=X; cc,dc=O; ec,fc=X; gc=O; hc,ic=X
        ",,XXXXXXX",  # d(3): cd..id = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["ab", "ac", "bc", "ga", "fa", "gb", "gc"])

    # Simpler probe: on right wing, White needs to throw-in or hane at `ga` BEFORE playing `ba`!
    # Why would `1.W[ba]` fail unless `1.W[ga]` is played first?!
    # Suppose `1.W[ba]` is answered by `2.B[ga]` (connecting `gb` out to `ha=X`, after which `fb` is no longer a false-eye/capture so W lacks 2nd eye!),
    # WHEREAS `1.W[ga]` puts `fb=X`? YES!!
    # Look: if `fb = X` (an isolated Black stone!) has liberties `ea`, `fa`, `ga`?
    # Trace: `eb=O, ec=O, fc=O, gb=O`, and `fb = X` sits inside White's belly with `fa = .` above it!
    #   a(0): . . O . O . . X   (aa=., ba=., ca=O, da=., ea=O, fa=., ga=., ha=X)
    #   b(1): X O . O O X O X   (ab=X, bb=O, cb=., db=O, eb=O, fb=X, gb=O, hb=X)
    #   c(2): X X O O O O O X   (ac,bc=X; cc,dc,ec,fc,gc=O; hc=X)
    #   d(3): , , X X X X X X   (cd..hd = X)
    # TRACE THIS!!
    # - `fb = X` only has 1 liberty `fa`!
    # - `gb-gc-fc-ec-dc-cc` is connected to `db-eb-ea`!
    # - Wait: if `1.W[ga]` (1st-line hane!), `2.B[fa]` connects? No, `fa` only has `ga`!
    # Make `gb = X` (Black outer wall!), so `fa` has `ga` connecting to `ha=X`!
    #   a(0): . . O . O . . X   (aa=., ba=., ca=O, da=., ea=O, fa=., ga=., ha=X)
    #   b(1): X O . O O X X X   (ab=X, bb=O, cb=., db=O, eb=O, fb=X, gb=X, hb=X) -> fb is connected to gb!
    # Instead: `gb = .`, `hb = X`, `fc = O, gc = O`, so `fb = X` can ONLY escape via `fa-ga-ha` OR `gb-hb`!
    analyze_deep("P08-probe-2", [
        "..O.O..X,",  # a(0): aa=., ba=., ca=O, da=., ea=O, fa=., ga=., ha=X
        "XO.OOX.X,",  # b(1): ab=X, bb=O, cb=., db=O, eb=O, fb=X, gb=., hb=X
        "XXOOOOXX,",  # c(2): ac,bc=X; cc,dc,ec,fc=O; gc,hc=X
        ",,XXXXX,,",  # d(3): cd..gd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["ab", "ac", "bc", "fb"])

    analyze_deep("P08-probe-3", [
        "..O..O.X,",  # a(0): aa=., ba=., ca=O, da=., ea=., fa=O, ga=., ha=X
        "XO.OO..X,",  # b(1): ab=X, bb=O, cb=., db=O, eb=O, fb=., gb=., hb=X
        "XXOOXXXX,",  # c(2): ac,bc=X; cc,dc=O; ec..hc=X
        ",,XXXX,,,",  # d(3): cd..fd = X
    ], r0=0, c0=0, first="W", defender="W", cap_coords=["ab", "ac", "bc", "fa"])
