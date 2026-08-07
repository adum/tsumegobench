# Controlled model prompt

The benchmark runner supplies everything below the line together with the same 20 reference SGFs for every model run.

---

You are being evaluated on your ability to create original Go (baduk/weiqi) problems.

Create the exact number of simple, local life-and-death problems specified in `inputs/task.md`. The supplied SGFs are style references only. Do not copy, translate, rotate, reflect, recolor, lightly edit, or combine their positions or solution paths.

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

Originality is a hard requirement. No output may duplicate another problem in this run or any problem on GoProblems. A duplicate includes a translation, rotation, reflection, color reversal, lightly altered setup or tree, or a position with the same tactical core disguised by inconsequential stones or changes around the edge.

Use the supplied originality query tool while authoring and once more on every exact final file after the complete set exists. Built-in common-position checks use only the initial setup and may reject a known shape before inspecting its paths. Otherwise, GoProblems can check a candidate only when its solution tree contains at least one accepted path marked with uppercase `RIGHT`, so finish and mark a valid solution path before querying. An unmatched request without `RIGHT` returns a `missing-right` error and consumes query budget. Only `clear` is an acceptable final result; `review`, `duplicate`, `invalid`, `unavailable`, and `quota_exceeded` are not. Replace or materially redesign a flagged candidate rather than trying to evade the check with irrelevant stones. Do not edit a file after its final clear result. The exact query budget and file protocol are given in `inputs/task.md` and `inputs/originality-tool.md`.

SGF requirements:

1. Put no move and no `C[...]` comment at the root. Do not write a problem instruction; the board position and first-move color must make the ordinary life-and-death objective clear.
2. Every node after the root must contain exactly one `B` or `W` move.
3. Alternate colors, use one consistent first-player color, and include no pass moves.
4. `RIGHT` is the only control marker in this benchmark. Mark every accepted solution endpoint with uppercase `RIGHT` inside `C[...]`; variations without it are treated as wrong.
5. Include every materially distinct solver move and continuation that achieves an equally valid best result. Do not omit a valid solution, hide it behind move ordering, or place it in a wrong branch.
6. For every accepted solver choice, cover the strongest and materially distinct defenses needed to establish that it works under best resistance.
7. End a correct path at the first natural position where the intended life, death, seki, or ko result is forced and clear. Do not stop before the result is established, and do not continue through routine cleanup after it is settled. A final capture is unnecessary when the status is already unambiguous.
8. Give comparable care to refutation coverage. Include plausible level-appropriate wrong solver moves and the meaningful opponent replies that show why they fail.
9. End a wrong path on the opponent's refuting move, or at the first position where failure is forced and clear. Do not stop on the mistaken solver move before demonstrating its consequence, and do not add redundant continuation after the refutation is established.
10. Use plain UTF-8 text with no HTML or JavaScript.
11. Check captures, liberties, occupied points, and the final life/death result on every branch.

Across the requested problems, demonstrate a deliberate range of difficulty rather than clustering at one level. Follow the per-file target difficulties listed in `inputs/task.md`; the default ten-problem run assigns two problems to each band from 20–30 kyu through about 1 dan. Difficulty should come from relevant reading depth, plausible choices, defenses, and endpoint judgment—not from irrelevant stones, obscure rules, or trick wording.

Across the set, include at least two Black-to-play and at least two White-to-play problems. Establish the player color only through the first move in the tree, not through written instructions. Vary the board edge/corner shape and tactical idea. Do not explain your reasoning and do not claim that you searched for duplicates unless you actually used the supplied originality tool.

Write exactly the files listed in `inputs/task.md` and no others. Each file must contain only one complete SGF collection beginning with `(;` and ending with `)`—no Markdown fences or explanatory prose. Your final command-line response may only confirm that the requested files were written; the files themselves are the benchmark output.
