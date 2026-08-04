# Authoring guide: what counts as a good problem

This guide adapts the public GoProblems construction rules to a deliberately narrow AI benchmark. The source articles remain authoritative for GoProblems itself; limits labeled **benchmark-specific** exist to make model runs comparable.

## 1. Scope

An accepted candidate is all of the following:

- **Life and death:** an entire local group must live or die.
- **Standard:** local, tactical, realistic, understandable without unusual rules, and with a clear outcome.
- **Candidate-canonical:** correct, complete, well-formed, useful to solve, and free of known flags. “Canonical” is earned through review; a model cannot establish it merely by writing the word.
- **Simple:** aimed roughly at 30–10 kyu, with a compact local position and a short, legible tree.
- **Original:** not an exact, transformed, translated, color-reversed, or near duplicate of an existing problem.

Do not submit whole-board best-move, joseki, fuseki, endgame, contrived-rule, trick-question, or “find a particular coordinate” problems.

Source: [Types of Problems](https://www.goproblems.com/article/problemtypes) and [Problem Construction Best Practices](https://www.goproblems.com/article/bestpractices).

## 2. SGF contract

Use UTF-8 SGF. A problem begins with a root setup position and then branches into alternating moves.

Required:

- A square `SZ` of 9, 13, or 19; omitted `SZ` means 19.
- Both `AB` and `AW` setup stones at the root.
- No move at the root.
- Exactly one `B` or `W` move at every later node.
- Alternating black and white moves.
- One consistent first-move color across all first branches.
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

When no special instruction is given, the ordinary life-and-death objective applies. Prefer the best unconditional local result.

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

- Correct lines normally end on the protagonist's move.
- Wrong lines normally end on the antagonist's refutation.
- Put explanatory comments on a computer response or at a leaf. A comment on the solver's move may not be displayed before an automatic reply.
- The first child is the default automatic response; use `CHOICE` when more than one defense should be tested.
- Cover the plausible mistakes a solver at the target level is likely to try.
- Do not add branches that teach nothing or differ only cosmetically.
- Confirm every branch against the actual board state, including captures and liberties.

## 5. Simplicity envelope

These are **benchmark-specific** comparability limits, not GoProblems rules:

- At most 14 moves on the longest line.
- At most 120 total nodes.
- Prefer 48 or fewer setup stones.
- Keep the tactical area local and the intended group visually obvious.
- Avoid requiring an introductory instruction; the default objective should be enough.

A warning does not automatically reject a problem, but a reviewer must explain why exceeding a preference improves the problem.

## 6. Originality

Before scoring, run both checks:

1. **Local corpus check:** canonicalizes translations, rotations, reflections, color reversal, and branch order.
2. **GoProblems check:** sends the SGF as `pattern` to `/api/v2/problems/similar` with radius 2, then to `/api/v2/problems/similar-percentage`.

Any radius-2 match fails the default gate. A percentage match of 90% or more also fails; 80–89% requires manual comparison. These conservative thresholds make it harder for a model to pass by lightly editing a known shape.

Source: [Solution Signatures](https://www.goproblems.com/article/solutionsignatures) and [API access](https://www.goproblems.com/article/api).

