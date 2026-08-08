P4:

```
  a b c d e f
a W B B B O .
b W W . B O .
c B B B B O .
d B B B B O .
e B B B B O .
f O O O O O .
```

Wait AW: aa ab bb, ea-ee ef df cf bf af
AB: ba ca da, ac bc cc dc, ad-dd, ae-de

```
a W B B B O
b W W . B O  - bb is W! so 
```

bb is AW white - so white is aa, ab, bb - 3 stones.
Empty: cb

White aa-ab-bb connected. Libs:
aa: ba B, ab - corner, only through ab
ab: aa, bb, ac B, (b empty? ab right = bb W)
bb: ab, cb empty, ba B, bc B
Only lib cb!

Black libs: cb and db (db empty - db not in AB/AW)
db empty yes. Black has cb and db at least.

B[cb] captures white 3 stones. RIGHT.
B[db]; W[cb] captures black if black only has those 2 libs.

Check all black libs:
ba: aa W, bb W, ca, (off? ba is row a - edge) ba down=bb W
ca: ba, da, cb empty, (c, something)
da: ca, ea W, db empty
ac: ab W, bc, ad, (off left? ac is col a)
etc.

Could have more libs at something... af is W. 
What about fa empty? fa not adjacent to black necessarily.

Black stones extend to de, ce, etc. de right = ee W. 
Maybe lib at df? df is W.

Possibly only cb and db. Good enough - verify with tool.

If black has more than 2 libs, W[cb] after B[db] doesn't capture black, just saves white by... W[cb] captures? White was in atari at cb only, after B[db] white still has only cb, W[cb] is suicide. So the refutation B[db];W[cb] only works if W[cb] captures black (making it legal by capturing).

Black must have only libs cb and db. Let me verify no other black libs.

Black: ba,ca,da, ac,bc,cc,dc, ad,bd,cd,dd, ae,be,ce,de

Check each for empty neighbors:
ba: aaW, ca, bbW, edge - no empty
ca: ba, da, cb empty, bbW - lib cb
da: ca, eaW, db empty, da down=db - lib db  
ac: abW, bc, ad, edge - no empty
bc: ac, cc, bbW, bd - no empty
cc: bc, dc, cb empty, cd - lib cb
dc: cc, ec? ec not in lists - EMPTY! dc right = ec empty!

ec is empty and adjacent to dc! Black has liberty ec!

Need AW or AB at ec. Add ec to AW (wall).