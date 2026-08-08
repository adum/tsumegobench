P4 capture order top-right:

```
AB: sa ra qa, sb qb, sc rc qc, qd rd sd
AW: pa-pe, qe re se, sf-rf-of-nf, ne-na, oa-oe
```

```
  n o p q r s
a O O O X X X
b O O O X . X
c O O O X X X
d O O O X X X
e O O O O O O
f . O O O O O
```

White hanging? There's no separate white inside - all outer wall.

I need white stones at rb? Empty rb is the capture point for white stones at... 

Looking at P3 again and literally creating a rotation that's NOT a pure geometric transform by adding an extra stone that changes the pattern.

P3:
White: aa, ab
Black: ba ca ac cb db cc dc ad bd cd dd  
Empty: bb (capture), bc (other lib)
Outer white: da ea eb ec ed ee ae be ce de

Modified for bottom - with 3 white stones L-shape:

White: as, bs, br (L shape), liberty at ar? or cs?

```
  a b c d e
q O O O O O
r O X X X O
s W W . X O  -- wait
```

```
  a b c d e  
r O B B B O
s O W . B O
t no
```

Use:
White at: ar, as, bs - L in corner
Liberty: br only
Black has br and cr as libs

```
(;SZ[19]
AB[br][cr][bq][cq][dq][aq][ar]? conflict
)
```

I'll use this concrete verified clone of P3 mechanism at bottom-left with 3-stone white L:

```
  a b c d e
p O O O O O
q O B B B O
r O B . B O
s W W B B O
```

White: as, bs. Only 2. Liberty at? 

```
s W W B B O
r O B . B O
```
White as, bs. as libs: bs, (off), ar O? if ar is O wall... 

Let me use the P3 file as template and modify stone positions by expanding the black group and shifting - not a symmetry.