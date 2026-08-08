P6 bottom-right capture order:

```
AB: ss sr rr, qs qr qq, pq pr ps, os ns nr nq oq
AW: rs, sq sp rp qp pp op np mp mq mr ms ls lr lq lp
```

```
  l m n o p q r s
p O O O O O O O .
q O O O X X X O X? sq O, rq empty?, qq X
r O O O X X X X X
s O O O X X X O X? rs O, ss X
```

White rs - single stone?
rs neighbors: qs X, ss X, rr X, (off) - 0 libs! Illegal - already captured.

White rs in atari with no libs means illegal setup.

White needs the liberty rq empty as their only lib:
rs neighbors must include rq - rs is (r,s), rq is (r,q) - not adjacent (row s vs q).

Liberty at rr? rr is black.

For white at rs, ss - but ss is black.

Hanging white at rs only, liberty at rr - but rr black.

White at sq, sr with liberty rq:
sr: rr B, ss B, sq, (off) 
If sr white and ss black...

```
AW: rs only, liberty qs - qs is black.

I'm going in circles. Let me copy P3 exactly and only change by adding 2 extra black stones in the fighting group and 1 extra white in the wall - non-symmetric expansion of P3.
