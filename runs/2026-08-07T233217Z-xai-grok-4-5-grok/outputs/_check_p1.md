# P1 analysis

Board bottom-left:

```
   a b c d e f
p  . X X X X X
q  X O O O O X
r  X O . . O X
s  X . O O X X
```

AB: bp cp dp ep fp, aq fq, ar fr, as es fs
AW: bq cq dq eq, br er, cs ds

White stones: bq-cq-dq-eq-br-er-cs-ds
Connected? br-bq yes. er-eq yes. cs-ds yes. cs to br? cs neighbors: bs empty, rs, cr empty, ds. NOT to br (br is b,r - cs is c,s). 
ds to er? ds=(d,s), er=(e,r) - not adjacent. ds up=dr empty, ds right=es(B).

CONNECTION PROBLEM: cs-ds are separate from upper white unless connected through empties... 
Upper: bq cq dq eq br er
cs connected to? only ds among white. SEPARATE two-stone group on bottom!

Need fix: add cr as white OR bs as white OR connect via dr.

Revised AW: bq cq dq eq br er cr? or ds cs and dr.

Better shape - "almost two eyes":

```
   a b c d e f
p  . X X X X X
q  X O O O O X
r  X O . . O X
s  X O . O X X
```

AW: bq,cq,dq,eq, br,er, bs, ds
AB: bp,cp,dp,ep,fp, aq,fq, ar,fr, as,es,fs

White: bq-cq-dq-eq-br-er-bs-ds
bs-br connected. ds-? ds to er via? ds up=dr empty, ds to eq? no. ds to er: er is (e,r), ds is (d,s) - diagonal only.
ds not connected! Add dr as white:

AW: bq cq dq eq br er bs ds dr

```
   a b c d e f
p  . X X X X X
q  X O O O O X
r  X O . O O X
s  X O . O X X
```

Then eye space: cr, cs. White has almost two eyes.
cr and cs - if both empty, are they two eyes?
cr neighbors: br(O), er? cr right=dr(O), cq(O), cs(empty). All white or empty - cr is eye if cs not needed.
Actually cr neighbors: cq(O), br(O), dr(O), cs. True eye!
cs neighbors: cr, bs(O), ds(O), (off). True eye!

White already has two eyes (cr and cs)! Already alive - black cannot kill.

Opposite problem.

For black to KILL a group that would live if black fails:

White shape with false eye potential:

```
   a b c d e f
p  X X X X X X
q  X O O O O X
r  X O . O . X
s  . . O . . X
```

Let me try:

```
   a b c d e f g
p  X X X X X X .
q  X O O O O X .
r  X O . . O X .
s  X . . O . X .
```

AW: bq cq dq eq, br er, ds
Hmm ds only connected through empties...

AW: bq,cq,dq,eq,fq wait.

I'll use this working kill shape - "carpenter's square" variant or simple:

## Working P1: Black kills, white has 3 libs and false eye

From a known-good easy mechanism - "place inside the eye space to reduce to dead shape":

```
   c d e f g h
p  X X X X X X
q  X O O O O X
r  X O . . O X
s  X O . O O X
```

AW: dq eq fq gq, dr gr, ds fs gs
AB: cp dp ep fp gp hp, cq hq, cr hr, cs hs, is? 

```
  c d e f g h
p X X X X X X
q X O O O O X
r X O . . O X
s X O . O O X
```

White connected: dq-eq-fq-gq-dr-gr-ds-fs-gs. 
gs-gq via gr. fs-fq? fs up=fr empty - fs to gs yes, fs to ds via es empty - fs-gs-gr-gq-fq. Yes.
ds-dr yes.

Eye space: er, fr, es.
Libs also: maybe none external if sealed.

Is hs black? Yes. cs black.

White libs = er, fr, es only (3 points inside).

Can white live? With 3-point eye space in a row (er,fr and es) - the shape is like "bent three" or "rabbity six" fragment.

If B[er]: kills often.
If B[fr]: 
If B[es]:

Reading "3-space L" or "T" shape:
Points: er, fr, es - an L-shape three (er-fr and er-es? er-es not adjacent - er=(e,r), es=(e,s) yes adjacent! fr=(f,r) adjacent to er.

So points er, fr, es form a bent three (L tromino).

Bent three eye space is dead - killer plays in the middle of the bent three which is er (the bend point).

B[er] kills:
After B[er], remaining fr and es are separate false eyes / atari points.

If W[fr], black B[es] captures or vice versa.

If black wrongly plays B[fr] first:
W[er] - white takes the vital point and gets an eye, may live with es.

After W[er]: white has solid connection, eye space es and maybe fr is now... fr neighbors er(W), so fr can be second eye?
fr neighbors: er(W), fq(W), gr(W), fs(W). ALL white! fr is a true eye!
es neighbors: er(W), ds(W), fs(W), off. ALL white! True eye!

So if black fails to play er, white W[er] lives with two eyes (fr and es)! Perfect!

Correct: B[er] kills.
Wrong: B[fr]; W[er] lives
Wrong: B[es]; W[er] lives  
Wrong: B[fs] occupied

After B[er], does white die for sure?
White remaining libs: fr, es.
If W[fr]: then only lib es - black B[es] captures all.
If W[es]: only lib fr - black B[fr] captures.
If W plays elsewhere, black takes either and continues.

Does B[er] capture immediately? No, white has 2 libs. But white is dead (dead shape). Endpoint: B[er] is enough to establish death? For beginners, maybe show one more move.

Per guidelines: end when status is forced and clear. After B[er], white has two separated liberties - classic dead. For 25 kyu, showing B[er] as RIGHT is OK if death is clear; or continue W[fr] B[es] C[RIGHT].

Looking at easy refs - gp-53750 ends on the single killing move. I'll end on B[er]C[RIGHT] and also show refutations.

Also check: is there another killing move?
B[fr]: W[er] lives - wrong.
B[es]: W[er] lives - wrong.

Good problem!

Verify AB wall complete:
Need left of c: or start at c is fine if cq,cr,cs black.
Right: hq,hr,hs black. hp black. What about g-s gs is white, hs black.

Top sealed p-row. Good.

White stones list:
dq,eq,fq,gq, dr,gr, ds,fs,gs

Black:
cp,dp,ep,fp,gp,hp,
cq,hq,
cr,hr,
cs,hs

Is that enough on the right of gq? hq black yes. 
Left of dq: cq black.

gs white at (g,s) - neighbors: fs(W), hs(B), gr(W), off. OK.

fr empty, er empty, es empty.

Double-check white liberties only er,fr,es:
dq: cq(B), eq, dp(B)? dq up=dp(B), dr(W) - OK no extra lib
eq: dq,fq, ep(B), er(empty) - lib er
fq: eq,gq, fp(B), fr(empty) - lib fr
gq: fq, hq(B), gp(B), gr(W)
dr: dq, cr(B), ds(W), er(empty) - lib er
gr: gq, hr(B), gs(W), fr(empty) - lib fr
ds: dr, cs(B), es(empty), off - lib es
fs: es(empty), gs(W), fr(empty), off - libs es, fr
gs: fs, hs(B), gr, off

Yes libs = {er, fr, es}.

Perfect!
