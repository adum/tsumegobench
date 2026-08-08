P5: Black kills - bent three on bottom with white stones

```
  a b c d e f g
p X X X X X X X
q X O O O O O X
r X O O . O O X
s X X . . . X X
```

AW: bq cq dq eq fq, br fr, cr er
Empty: dr, cs, ds, es

Wait I have cr and er as white - so
```
r X O O . O O X
```
cr=O, dr=., er=O

Empty: dr, cs, ds, es

That's 4 empties - not bent three!

AW in file: bq cq dq eq fq, br fr, cr er
Missing ds as white etc.

Diagram from file:
AB: ap-gp, aq gq, ar gr, as bs fs gs
AW: bq cq dq eq fq, br fr, cr er

```
  a b c d e f g
p X X X X X X X
q X O O O O O X
r X O O . O O X
s X X . . . X X
```

Empty: dr, cs, ds, es, and hs? gs is X, fs X. Also er is O.

Eye space: dr, cs, ds, es - 4 points in a T or square-ish:
cs-ds-es on bottom, dr above ds.

This is the **T-shaped four** (or pyramid-related).

T-four shape empties: {cs, ds, es, dr} - T with stem upward.

From theory: **T-shaped four is a dead shape** (dead even if defender plays first?). Or unsettled?

Actually I believe the T-shape four (tetris T) as eye space is dead - the killer plays at the center ds.

If B[ds]: kills.
If white W[ds] first: still may be dead or ko.

Let me check if unsettled...

Upon thinking: the four-point T eye space - defender to move plays at the center and gets a straight three remaining which is still dead. So **completely dead**. Bad.

If B[dr] as I wrote - is that correct?

I need to fix to bent three only 3 empties.

### Fix P5 to bent three with extra surrounding complexity:

```
  a b c d e f g
p X X X X X X X
q X O O O O O X
r X O . . O O X
s X O . O O X X
```

Empty: cr, dr, cs - bent three bend at cr? 
cr-dr adj, cr-cs adj. Yes bent three at cr.

AW: bq-fq, br fr er, ds es, bs? bs empty no
```
r X O . . O O X  - br O, cr ., dr ., er O, fr O
s X O . O O X X  - as X, bs O, cs ., ds O, es O, fs X, gs X
```

AW: bq cq dq eq fq, br er fr, bs ds es
Empty: cr, dr, cs

Bent three {cr,dr,cs}, bend cr. Vital B[cr].

But wait is {cr,dr,cs} bent three?
cr-dr yes, cr-cs yes, dr-cs diagonal. Yes L.

B[cr] kills. W would live with W[cr].

Is there connection of all white? bq-cq-dq-eq-fq-fr-er-br, bs via br, ds-es via... ds to es yes, ds to er via? ds up=dr empty, ds to fr? no. es-er yes. ds-es-er-fr. Good.

Write clean SGF.
