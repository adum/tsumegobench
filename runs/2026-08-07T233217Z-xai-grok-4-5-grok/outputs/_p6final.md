P6 W to capture black hanging aa,ab,ac:

```
  a b c d e f
a B W B O O O? da is B - 
a B W . O B .
```

AB: aa ab ac, da ea, eb-ee, ae be ce de, af-ef
AW: ba ca cb db cc dc ad bd cd dd

```
a B W B O B .
b B W W O B .
c B W W O B .
d . W W O B .
e O O O O O .
f O O O O O .
```

Wait ae is B on row e? ae is (a,e)=B. de B. 
ee is B? ee is in AB as eb ec ed ee - yes.

Hanging black aa-ab-ac vertical on left edge.
aa-ab-ac: ac down=ad W, so stops. Separated from ae by ad W. Good.

Libs of hanging: 
aa: ba W, ab, edge - no empty
ab: aa, ac, bb empty, ba W - lib bb
ac: ab, ad W, bc empty, aa path - lib bc!

Hanging has libs bb AND bc! 2 libs, not 1. So not in atari.

Need to block bc as black liberty - put white or black at bc, but bc is white's second lib for the fight...

If bc is white stone: then hanging only has bb. White has libs?

Actually for capture order:
- Hanging black has 1 lib L1
- White has L1 and L2

If hanging has only bb, put white at bc... then white stone at bc is part of white group. White libs?

Let me put AB at bc to seal hanging, and white's second lib is something else like cb... 

Standard P3 structure color-reversed carefully.
