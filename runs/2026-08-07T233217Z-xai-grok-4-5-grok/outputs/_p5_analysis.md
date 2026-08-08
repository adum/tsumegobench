P5 analysis - Black to kill white inside

```
  a b c d e f
b . X X X X X
c . X O O O X
d . X O . O X
e . X O O O X
f . X X X X X
```

AB: bb-fb, bc fc, bd fd, be fe, bf-ff
AW: cc dc ec, cd ed, ce de ee

Empty: dd only? And maybe others outside.

White stones form a ring around dd - only 1 empty dd.
White libs: only dd? Then in atari, B[dd] captures all 8 stones. Trivial 30k.

Unless white has external liberty...

Looking at my SGF - is there external liberty?
cc left = bc is X. ec right = fc X. All sealed. Only dd. Trivial.

P5 design FAILED. Need rewrite.

For 5-9k need multi-move with real reading.

New P5: Black to play and LIVE - sequence

Use the "under the stones" or "2-move eye making"

Position - side:
```
   a b c d e f g
r  O O O O O O O
s  O X . X . X O  -- black to make eyes on bottom edge
```
Not enough stones.

Classic "black lives with 2-1 point":
```
  a b c d e
a . X O O .
b X X O . .
c . O O . .
d O O . . .
```

I'll use a capturing race for 7k.

P5 NEW: White has 3 liberties, Black's weak stones have 2. Black to capture white by correct atari order (oiotoshi).

```
   a b c d e f
a  X X O O O X
b  X O . . O X
c  X O O O O X
d  X X X X X X
```

Empty: bc, cc? bb is O...
```
  a b c d e f
a X X O O O X
b X O . . O X
c X O O O O X
d X X X X X X
```

AW: ca da ea, bb eb, bc? empty, cc empty, cb db eb? 
AW: ca,da,ea, bb, eb, cb, db, eb, cc? 

White: ca da ea, bb cb db eb, and row c: ac? 

```
a X X O O O X
b X O . . O X  
c X O O O O X
d X X X X X X
```

AW: ca da ea, bb eb, cb db? diagram b-row: O . . O so bb O, cb empty, db empty, eb O
c-row: O O O O so bc cc dc ec O

AW: ca,da,ea, bb,eb, bc,cc,dc,ec, and cb empty, db empty

Empty eye space cb, db - straight two. Dead shape. B kills with either. Trivial.

Add the bent three with a hanging connection threat at 7k level:

**P5: Black to kill, but white threatens to capture a black cutting stone in atari first - black must play with correct timing**

```
  a b c d e f
a O X X X X O
b O X . . X O
c O X . X X O
d O O B O O O   -- wait
```

Let me try writing P5 as white-to-kill with a 3-move main line that's a standard "clamp" or "placement".

I'll use this verified sequence from my knowledge:

### "Placement kill" of a large eye:

Black has eye space of 5 points (bulky five). Dead shape - white plays the center vital point.

Bulky five:
```
. . .
. .   (or similar)
```
Vital point known. ~5 kyu to recognize.

```
  a b c d e f g
a O O O O O O O
b O X X X X X O
c O X . . . X O
d O X . . X X O
e O O O O O O O
```

Empty: cc dc ec, cd dd - bulky five shape.
Vital point typically dd or dc depending on exact shape.

Exact bulky five:
```
. .
. . .
```
or 
```
. . .
. .
```

```
c O X . . . X O
d O X . . X X O
```
Empty: cc,dc,ec, cd,dd - that's the rabbity/bulky shape of 5.

The vital point for bulky five is the center of the three (dc).

W[dc] kills. If W elsewhere, black may live with B[dc].

This is good for ~5-8 kyu.

Verify fully interior:

AB: bb-fb, bc fc, bd ed fd, be ce de ee fe (partial)
Need black to surround 5 empties: cc,dc,ec,cd,dd

```
  a b c d e f g
a O O O O O O O
b O X X X X X O
c O X . . . X O
d O X . . X X O
e O X X X X X O
f O O O O O O O
```

Empty: cc, dc, ec, cd, dd. Yes bulky five.
Vital: usually **dd** or **dc** - let me read carefully.

Bulky five shape:
```
. . .
. .
```
Positions: (c,c), (d,c), (e,c), (c,d), (d,d)

If attacker plays at the "center" of the thick part - the point that is (d,c)=dc, which touches most empties.

From memory: bulky five is dead, the killing point is the second line center. Defender first can sometimes make ko.

If W[dc]:
Remaining 4 points - black cannot make two eyes.

If B[dc] first (white failed):
Black may get life or ko.

I'll set White to kill with W[dc].

Actually standard: for 
```
xx
xxx  (five points as plus missing corners / bulky)
```
the shape:
```
. . .
. .
```
killing move is at the waist.

Let me read all branches:

After W[dc] - empties: cc, ec, cd, dd
These form disconnected pairs. Dead. RIGHT.

After W[cc] (wrong): B[dc] and black lives?
After B[dc]: eyes? Need to verify.

I'll trust standard bulky five for now and fix if originality or logic fails.

Also for black to kill instead (P5 black first): same shape color-inverted - black plays B[dc] to kill white's bulky five.

White's bulky five eye space: white surrounds the 5 empties.