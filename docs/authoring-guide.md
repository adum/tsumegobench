# Authoring guide: what counts as a good problem

This guide adapts the public GoProblems construction rules to a deliberately narrow AI benchmark. The source articles remain authoritative for GoProblems itself; limits labeled **benchmark-specific** exist to make model runs comparable.

## 1. Scope

An accepted candidate is all of the following:

- **Life and death:** an entire local group must live or die.
- **Standard:** local, tactical, realistic, understandable without unusual rules, and with a clear outcome.
- **Candidate-canonical:** correct, complete, well-formed, useful to solve, and free of known flags. “Canonical” is earned through review; a model cannot establish it merely by writing the word.
- **Bounded difficulty:** aimed between 30 kyu and 1 dan, while retaining a compact local position and a short, legible tree.
- **Original:** not an exact, transformed, translated, color-reversed, or near duplicate of an existing problem.

Do not submit whole-board best-move, joseki, fuseki, endgame, contrived-rule, trick-question, or “find a particular coordinate” problems.

Source: [Types of Problems](https://www.goproblems.com/article/problemtypes) and [Problem Construction Best Practices](https://www.goproblems.com/article/bestpractices).

## 2. SGF contract

Use UTF-8 SGF. A problem begins with a root setup position and then branches into alternating moves.

Required:

- An explicit `SZ[19]` root property. Every benchmark problem uses a 19×19 board; omitted or alternate sizes are rejected.
- Both `AB` and `AW` setup stones at the root.
- No move at the root.
- Exactly one `B` or `W` move at every later node.
- Alternating black and white moves.
- One consistent first-move color across all first branches.
- No root `C[...]` property or written problem instruction.
- No pass, occupied-point, off-board, or suicide moves.
- At least one uppercase `RIGHT` marker in a comment (`C[RIGHT]`).
- Plain-text comments only—no HTML or JavaScript.

Supported problem properties are `B`, `W`, `AB`, `AW`, `AE`, `C`, `LB`, `TR`, `MA`, and `SZ`; normal root metadata such as `FF`, `GM`, `CA`, and `AP` is also accepted. Other properties are ignored by GoProblems and produce a benchmark warning.

Source: [Problem Construction Basics](https://www.goproblems.com/article/constructionbasics).

### Control markers

- `RIGHT` marks a correct result. Any variation without a `RIGHT` is wrong by default.
- `CHOICE` lets the replying side choose among marked responses. Use it when the solver must handle multiple meaningful defenses.
- `FORCE` restricts the solver to enumerated moves.
- `NOTTHIS` outlaws a move.

`FORCE` and `NOTTHIS` are supported but discouraged. Prefer a naturally complete tree with explicit refutations. Markers may share a comment, such as `C[RIGHT CHOICE]`.

## 3. Correctness semantics

No special instruction is permitted. The first move color identifies the solver, and the local shape must make it visually clear whether that player is trying to live or kill. The ordinary life-and-death objective applies, with the best unconditional local result preferred.

For living, the source guidance orders results approximately as:

1. Clean life with points
2. Seki
3. Favorable multi-step ko
4. Favorable one-step ko
5. Ko where the opponent takes first
6. Unfavorable multi-step ko

For killing, clean death comes first, then favorable kos, then unfavorable kos, with seki last. If two outcomes are in the same category, do not invent a context-dependent distinction unless the problem explicitly requires it—and explicit context usually makes the problem non-standard.

When uncertain between accepting and rejecting two outcomes of the same class, favor accepting both. The problem should test life-and-death understanding, not the author's hidden preference.

Source: [Problem Construction Best Practices](https://www.goproblems.com/article/bestpractices).

## 4. Tree quality

Tree construction is part of the problem, not bookkeeping after the key move is known. The reference SGFs are provided partly to calibrate the judgment involved: how much meaningful reading to include, which alternatives deserve branches, and where a line has proved enough to stop.

### Accepted-solution coverage

- Include every materially distinct solver choice that achieves an equally valid best result, both at the first move and later in the tree.
- Do not reject a correct move merely because it differs from the author's intended sequence or reaches the same result through another meaningful order.
- For every accepted choice, include the strongest defense and each materially distinct resistance needed to establish the result under best play.
- When multiple opponent replies matter, use `CHOICE` or explicit branches rather than silently assuming one response.

### Refutation coverage

- Cover the plausible mistakes a solver at the target level is likely to try, not every legal move on the board.
- Show the meaningful opponent reply that refutes each included mistake. A wrong branch is incomplete if it stops on the mistake without demonstrating why the move fails.
- Include materially distinct refutations and defensive ideas; omit branches that teach nothing or differ only cosmetically.
- A supposedly wrong path that still reaches an acceptable result is a correctness failure, not merely a missing comment.

### Choosing endpoints

- A correct line normally ends on the protagonist's move, at the first natural position where life, death, seki, or ko status is forced and clear to the target solver.
- A wrong line normally ends on the antagonist's refuting move, at the first position where the solver's failure is forced and clear.
- Do not end a branch before the relevant result has actually been established. The reader should not have to assume an unshown tactical sequence that could still change the outcome.
- Do not continue through routine captures, filling liberties, or cleanup after the result is settled. A line need not reach an empty board or a final capture when the status is already unambiguous.
- Endpoint judgment is contextual rather than a fixed move count. Compare against the reference trees and ask whether the final node proves the claim cleanly, neither one move too early nor several moves too late.

Keep comments inside the solution tree, on a computer response or at a leaf. A comment on the solver's move may not be displayed before an automatic reply. Confirm every branch against the actual board state, including captures and liberties.

## 5. Simplicity envelope

These are **benchmark-specific** comparability limits, not GoProblems rules:

- At most 14 moves on the longest line.
- At most 120 total nodes.
- Prefer 48 or fewer setup stones.
- Keep the tactical area local and the intended group visually obvious.
- Root instructions are prohibited; the position and first-move color must stand on their own.

A warning does not automatically reject a problem, but a reviewer must explain why exceeding a preference improves the problem.

## 6. Originality

Before scoring, run both checks:

1. **Local corpus check:** canonicalizes translations, rotations, reflections, color reversal, and branch order.
2. **GoProblems check:** sends the SGF as `pattern` to `/api/v2/problems/similar` with radius 2, then to `/api/v2/problems/similar-percentage`.

Any radius-2 match fails the default gate. A percentage match of 90% or more also fails; 80–89% requires manual comparison. These conservative thresholds make it harder for a model to pass by lightly editing a known shape.

Source: [Solution Signatures](https://www.goproblems.com/article/solutionsignatures) and [API access](https://www.goproblems.com/article/api).
