P1 new analysis:

```
AB: aq-eq, ar er, as es bs
AW: br cr dr, cs ds
```

```
  a b c d e f g h
q X X X X X . .
r X O O O X . .
s X X O O X . .
```

Wait bs is AB X, cs O, ds O, es X
```
s X X O O X
```

White: br cr dr cs ds - connected group
Libs: bs is X, so...
br: ar X, bq X, cr, bs X - no empty from br
cr: br, dr, cq X, cs
dr: cr, er X, dq X, ds
cs: cr, ds, bs X, (off)
ds: dr, cs, es X, (off)

ZERO liberties! Illegal setup - white already captured.

Need external liberty.

Add empty at fr or gr for white to have a lib, and black kills by taking it.

```
  a b c d e f
q X X X X X X
r X O O O O X
s X X O . O X
```

Or:

White has 2 libs, black takes the critical one.

```
AB: aq bq cq dq eq fq, ar fr, as es fs
AW: br cr dr er, cs ds
Empty: bs, and maybe rs

  a b c d e f
q X X X X X X
r X O O O O X
s X . O O X X
```

White: br-er, cs ds
Libs: bs (from br, cs), and maybe...

br left ar X, up bq X, right cr, down bs empty - lib bs
cs: bs empty, ds, cr, off - lib bs
Only 1 lib - atari. B[bs] captures. Too trivial but might be original position?

Add second lib:
```
s X . O O . X
```
Empty bs and es, with fs X
AW without er? 

```
r X O O O X X
s X . O O . X  
```

AW: br cr dr, cs ds
AB: aq-eq, ar er fr, as fs, and es empty, bs empty
```
  a b c d e f
q X X X X X .
r X O O O X X
s X . O O . X
```

White libs: bs, es. Two libs!
B[bs] kills (white cannot extend to es usefully if it's also atari situation)?

After B[bs]: white only es. W[es] - then libs? fr is X, er is X, fs X, off - W[es] might be suicide or have no libs.

After B[bs], W[es]: es neighbors ds W, fs X, er X, off - only connects to ds. Group libs after? None - suicide. So B[bs] kills cleanly.

After B[es]: white only bs. Same, W[bs] suicide. Both kill!

Is white unconditionally dead? W to play W[bs]: remaining lib es only. Still dead next. Yes unconditionally dead - bad problem.

Need white to be able to live if black fails - so white needs eye potential.

Back to bent three but with MORE irregular surrounding to avoid 90% match - add extra empty spaces and irregular walls that create different signature while keeping the tactic.

Or use a problem like P3 that cleared - hanging stone capture with different shape.