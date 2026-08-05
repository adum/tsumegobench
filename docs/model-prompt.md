# Controlled model prompt

Copy everything below the line into a fresh model conversation. Attach all 20 SGFs from `examples/canonical-life-and-death/` in the same message when the interface allows it.

---

You are being evaluated on your ability to create original Go (baduk/weiqi) problems.

Create exactly five simple, local life-and-death problems in SGF. The attached SGFs are style references only. Do not copy, translate, rotate, reflect, recolor, lightly edit, or combine their positions or solution paths.

The solution tree is a central part of the task, not an annotation added after finding the key move. Study the reference SGFs for how they cover materially distinct correct continuations, meaningful defenses, and plausible mistakes, and especially for where each path naturally ends. Match that standard of coverage and endpoint judgment without copying their content.

Each problem must be:

- a realistic standard life-and-death problem with a clear local outcome;
- approximately 30 kyu–1 dan in difficulty;
- legal under ordinary Go rules;
- on a 19×19 board, explicitly declared with `SZ[19]`;
- expressed as a root setup with both `AB` and `AW`, followed by a complete alternating solution tree;
- self-explanatory from the local position and the color of the first move;
- short: no more than 14 moves on any line and no more than 120 total nodes;
- original rather than a disguised known problem.

SGF requirements:

1. Put no move and no `C[...]` comment at the root. Do not write a problem instruction; the board position and first-move color must make the ordinary life-and-death objective clear.
2. Every node after the root must contain exactly one `B` or `W` move.
3. Alternate colors, use one consistent first-player color, and include no pass moves.
4. Mark every accepted solution endpoint with uppercase `RIGHT` inside `C[...]`. Variations without `RIGHT` are treated as wrong.
5. Include every materially distinct solver move and continuation that achieves an equally valid best result. Do not omit a valid solution, hide it behind move ordering, or place it in a wrong branch.
6. For every accepted solver choice, cover the strongest and materially distinct defenses needed to establish that it works under best resistance.
7. End a correct path at the first natural position where the intended life, death, seki, or ko result is forced and clear. Do not stop before the result is established, and do not continue through routine cleanup after it is settled. A final capture is unnecessary when the status is already unambiguous.
8. Give comparable care to refutation coverage. Include plausible level-appropriate wrong solver moves and the meaningful opponent replies that show why they fail.
9. End a wrong path on the opponent's refuting move, or at the first position where failure is forced and clear. Do not stop on the mistaken solver move before demonstrating its consequence, and do not add redundant continuation after the refutation is established.
10. Use `CHOICE` only when the opponent has multiple meaningful defenses the solver should handle.
11. Do not use `FORCE` or `NOTTHIS` unless a complete natural tree would be unreasonable.
12. Use plain UTF-8 text with no HTML or JavaScript.
13. Check captures, liberties, occupied points, and the final life/death result on every branch.

Across the set, include at least two Black-to-play and at least two White-to-play problems. Establish the player color only through the first move in the tree, not through written instructions. Vary the board edge/corner shape and tactical idea. Do not explain your reasoning and do not claim that you searched for duplicates unless you actually used a search tool.

Output only these five sections in order:

`problem-01.sgf`

```sgf
(;...)
```

Repeat that exact filename-plus-code-block format through `problem-05.sgf`. Do not add prose before, between, or after the five sections.
