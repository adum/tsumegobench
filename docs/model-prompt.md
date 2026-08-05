# Controlled model prompt

Copy everything below the line into a fresh model conversation. Attach all 20 SGFs from `examples/canonical-life-and-death/` in the same message when the interface allows it.

---

You are being evaluated on your ability to create original Go (baduk/weiqi) problems.

Create exactly five simple, local life-and-death problems in SGF. The attached SGFs are style references only. Do not copy, translate, rotate, reflect, recolor, lightly edit, or combine their positions or solution paths.

Each problem must be:

- a realistic standard life-and-death problem with a clear local outcome;
- approximately 30–10 kyu in difficulty;
- legal under ordinary Go rules;
- on a 9×9, 13×13, or 19×19 board;
- expressed as a root setup with both `AB` and `AW`, followed by a complete alternating solution tree;
- self-explanatory from the local position and the color of the first move;
- short: no more than 14 moves on any line and no more than 120 total nodes;
- original rather than a disguised known problem.

SGF requirements:

1. Put no move and no `C[...]` comment at the root. Do not write a problem instruction; the board position and first-move color must make the ordinary life-and-death objective clear.
2. Every node after the root must contain exactly one `B` or `W` move.
3. Alternate colors, use one consistent first-player color, and include no pass moves.
4. Mark every accepted solution endpoint with uppercase `RIGHT` inside `C[...]`.
5. Variations without `RIGHT` are treated as wrong.
6. Correct lines should normally end on the solver's move; wrong lines should normally end on the opponent's refutation.
7. Use `CHOICE` only when the opponent has multiple meaningful defenses the solver should handle.
8. Do not use `FORCE` or `NOTTHIS` unless a complete natural tree would be unreasonable.
9. Use plain UTF-8 text with no HTML or JavaScript.
10. Check captures, liberties, occupied points, and the final life/death result on every branch.

Across the set, include at least two Black-to-play and at least two White-to-play problems. Establish the player color only through the first move in the tree, not through written instructions. Vary the board edge/corner shape and tactical idea. Do not explain your reasoning and do not claim that you searched for duplicates unless you actually used a search tool.

Output only these five sections in order:

`problem-01.sgf`

```sgf
(;...)
```

Repeat that exact filename-plus-code-block format through `problem-05.sgf`. Do not add prose before, between, or after the five sections.
