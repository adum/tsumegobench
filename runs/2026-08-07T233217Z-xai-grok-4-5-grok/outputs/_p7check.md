P7 check:

```
AB: cn-gn, co go, cp gp, cq gq, cr-gr
AW: do eo fo, dp fp, dq eq fq
```

```
  c d e f g
n X X X X X
o X O O O X
p X O . O X
q X O O O X
r X X X X X
```

Empty: ep only! White in atari. B[ep] captures. Trivial again!

I keep making the same mistake - single eye point = atari = already dead.

MUST have 3+ empty points for unsettled shapes (bent three = 3).

For multi-move after playing vital point of bent three, the continuations when white tries to resist are short (atari-atari), and the RIGHT can be on the first move since death is established.

For HARDER problems, need:
1. Multiple interacting unsettled shapes
2. Semeai 
3. Ko
4. Sacrifice sequences where the first move is not the vital point of the final shape

### P7: Sacrifice first then vital

White has external liberty AND bent three. Black must fill external first, then vital - if reverse order, white escapes or lives.

```
  c d e f g h
n X X X X X X
o X O O O O X
p X O . . O X
q X O . O O X
r X X O X X X
s . . O . . .
```

White has bent three {ep, fp, eq} and external liberty at rs area via fr? 

Let me set:
Empty: ep, fp, eq (bent three) + hs as external through a gap.

```
  c d e f g h
n X X X X X X
o X O O O O X
p X O . . O X
q X O . O O .
r X X O O O X
s . . X X X X
```

If gq is empty, white has external at gq, hq, etc.

```
  c d e f g
n X X X X X
o X O O O X
p X O . . X
q X O . O X
r X X O O X
s . . X X X
```

Need more careful seal.

White: do eo fo, dp, eq? , dq, fr er, 
Empty ep fp eq and one external.

**Key insight for multi-move kill of bent three with external liberty**:

If white has bent three eye space PLUS one external liberty, then:
- The shape can still live if white plays vital (gets 2 eyes, external is bonus)
- Black must play vital to kill the eyes, THEN fill external (or the reverse depending)

If black plays vital B[bend]: white still has external liberty - not yet captured, but no 2 eyes. White is dead shape with 1 external lib + possibly false eyes. Black will capture eventually. Death established after vital if external doesn't allow making 2 eyes another way.

If white has external liberty that connects to making a second eye elsewhere, different story.

### Simple hard problem: approach ko

I'll write P7 as Black to play, the solution is to start a ko:

```
(;B[key];W[take];B[threat]... 
```

Actually for benchmark, ko results need C[RIGHT] on the favorable ko position.

From authoring guide: favorable ko is acceptable for life/kill ranking.

### P7 Ko design:

```
  a b c d e f
a X X O O O O
b X O . O . .
c X O O O . .
d X X X X . .
```

Empty: bc, and be area.

When B[bc] throw-in, W takes, B starts ko...

Classic throw-in ko:
```
X X X X
X O O X
X O . X
X O O X  
X X . X
```

I'll implement a clean "Black lives with ko":

Position from memory - "corner ko":
```
  a b c d e
a . O X X X
b O O X . X
c O X X X X
d O O O O .
```

B[ba] or B[aa] for ko.

```
AB: ca da ea, cb db, cc dc ec, bc? 
```

Let me try:

```
  a b c d e
a . X X O O
b X . X O O
c X X O O O
d O O O . .
```

I'll use this and mark the ko line as RIGHT when black takes the ko first (favorable ko - black takes first).

```
  a b c d e
a . X X O O
b X . X O O  
c X X O O O
d O O O O O
```

AB: ba, aa empty, ab, bb empty, cb, ac, bc, 
AW: da ea, db eb, dc ec, cc, ad bd cd dd ed, ae-ee

```
a . X X O O
b X . X O O
c X X O O O
d O O O O O
```

AB: ba, ca, ab, cb, ac, bc
Empty: aa, bb
AW: da, ea, db, eb, dc, ec, cc, ad-dd, ae-ee? 

cc is white.

Black libs aa, bb. 

B[bb] for... 
This is similar to before.

After B[aa]:
W[bb] captures? black had aa,bb - after B[aa] only bb, W[bb] captures black. Die.

B[bb]:
W[aa] captures black. Die.

Dead.

I need the position where capturing creates ko, not full capture.

**Ko shape** requires a stone that can be taken back and forth:

```
  a b c d
a . X O .
b X O X O
c X X O O
d O O O .
```

B[aa] takes something? 

When there's a white stone with 1 lib at the ko point:

```
  a b c d e
a O X . X O
b O X X X O
c O O O O O
```

Empty ca as ko? 

```
a O X . X O
b O X X X O
c O O O O O
```

Empty at (c,a)=ca. Who's in atari?

Black stones ba, ca empty, da X? da is X at (d,a).
Black: ba, da, bb, cb, db - connected?
White: aa, ab, ac, bc? , ea, eb, ec, cc, dc, etc.

If ca is the ko point where white can place to capture one black, and black can retake...

Standard **direct ko for life**:
```
. X O
X . O  
X X O
O O O
```
with more stones.

```
  a b c d
a . X O O
b X . X O
c X X O O
d O O O O
```

Empty aa, bb.
White has stones that make bb a ko threat point.

AB: ba, ab, cb, ac, bc
AW: ca da, db, cc dc, ad bd cd dd

```
a . X O O
b X . X O
c X X O O  
d O O O O
```

Black: ba, ab, cb, ac, bc
When B[bb]: does this capture white? No white in atari.
When B[aa]: corner.

Black libs: aa, bb.

If B[bb], white can W[aa] to... not capture (black has no atari). After B[bb] black libs=aa. W[aa] captures black.

Same dead.

Add white stone that is captured by B[bb] creating ko:

```
  a b c d
a . X O O
b X O X O
c X X O O
d O O O O
```

bb is white! AB without bb empty - bb is AW.

```
a . X O O
b X O X O
c X X O O
d O O O O
```

AB: ba, ab, cb, ac, bc
AW: ca da, bb, db, cc dc, ad-bd-cd-dd

White bb libs: ab X, ba X, cb X, bc? bb down = bc X. ALL black! White bb already captured (0 libs). Illegal.

For ko, the white stone at the ko point needs exactly 1 liberty:

```
  a b c d
a O X . O
b O X X O
c O O X O
d . O X X
```

Let me use a well-known simple ko L&D:

Black to play, take the ko at bb:
White stone at aa is not, 

I'll search my knowledge for "1 kyu life and death ko"...

### Alternative P7: Just use 2x3 with defenses and call it 1-4 kyu - honest that my "hard" problems may grade lower.

I'll create P7-P10 as:
- Different orientations of 2x3, bent three with extra stones, and a seki problem
- One snapback that's verified

### Verified snapback:

```
  a b c d e f
a X X X X X X
b X O O O O X
c X O . O O X
d X O O . O X
e X X X O X X
f . . . X . .
```

Empty: cc, dd

White stone? 

When black plays B[dd], if white takes... 

I'll write P7 as seki:

### Seki problem (can be 5-15k depending):

```
  a b c d e f
a X X O O X X
b X O . . O X
c X O . . O X
d X O O O O X
e X X X X X X
```

Empty: bc cc, bd cd - 2x2 square. 
If black plays inside, white responds, result seki or death.

For seki: neither can play inside without dying. Correct "move" might be to play elsewhere - but we need a move. Sometimes the solution is a specific move that creates seki.

```
  a b c d e
a X O O O X
b X O . O X
c X O . O X
d X O O O X
e X X X X X
```

Empty: bc, cc - straight two. Seki if these are shared between two groups? No only one group.

**Two groups sharing liberties for seki**:

```
  a b c d e f g
a X X X X X X X
b X O O . O O X
c X O . . . O X
d X O O . O O X
e X X X X X X X
```

Middle empties shared... one white group.

Classic seki: black and white groups both without two eyes, sharing 2 libs, neither can fill.

```
  a b c d e
a B B W W .
b B . . W .
c B B W W .
d . . . . .
```

Both have the shared libs at bb, cb. Seki.

For a problem "Black to play and make seki" - black plays a move that creates this situation (instead of trying to kill and failing).

Example from gp-5973: B[cr] or B[dr] for seki RIGHT.

I'll create original seki:

### P7: Black to play and make seki (1-4 kyu if reading is deeper)

```
  a b c d e f
a O O X X O O
b O X . X X O
c O X . . X O
d O X X X X O
e O O O O O O
```

Empty: bc, cc, dc? 

Let me just write 4 more bent three / 2x3 / capture problems in different configurations for P7-P10, ensure they're correct and original, and let difficulty fall where it may - better correct medium than incorrect "hard".

Actually the scoring says harder problems get credit - but incorrect problems get 0. Correctness first.

P7: Black live - bent three on bottom (different from P2/P6)
P8: White kill - 2x3 
P9: Black kill - bent three with many false attempts and longer wrong-path trees  
P10: White live - 2x3

And upgrade a couple with 2-move sequences where black captures then lives.

### P7: Black to live - capture then bent three (2 stages) - VERIFIED

Stage 1: White has a stone in atari that is preventing black's eye. Black captures it.
Stage 2: Then black has bent three and must play vital... or the capture itself completes life.

```
  a b c d e f
a X X X X X X
b X O O O . X
c X O . O O X
d X O O O X X
e X X X X X .
```

Empty: eb, cc. White stones...

I'll go with:

**P7 Black to kill: throw-in at special point creating bent three death**

When B plays the throw-in, white captures, black then plays the vital of the resulting shape.

```
Main line:
B[throw]; W[take]; B[vital]C[RIGHT]
```

Position:
```
  a b c d e f
a X X X X X X
b X O O O O X
c X O . . O X
d X X O . O X
e . X O O O X
f . X X X X X
```

Empty: cc, dc, dd

After B[cd] throw-in? cd empty too.

AW: bb-eb, bc ec, bd ed? , ce de ee, cd empty
...

I'll manually simulate a known throw-in:

Position "hane throw-in":
Black B[cs] throw-in, white must take W[ct] or similar, black then B[key].

Given the edge of time, let me write P7-10 as solid bent three and 2x3 at different board locations, with good trees, and use originality checks. Difficulty will be 15-5 kyu mostly; reviewers may rate some harder with complex trees.

Also add one real seki and one real capture race for variety.