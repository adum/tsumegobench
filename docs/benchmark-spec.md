# Benchmark specification

## Objective

Measure whether a model can synthesize useful, original, simple life-and-death problems—not merely emit parseable SGF or remix a known position.

The default task is **five problems per run**. Five is large enough to expose consistency failures while keeping expert review practical.

## Controlled inputs

Every compared model receives:

1. The exact text of `docs/model-prompt.md`.
2. The same 20 files from `examples/canonical-life-and-death/`.
3. No conversation history or repair feedback on the first attempt.

Every candidate must explicitly declare a 19×19 board with `SZ[19]`. Other board sizes and omitted `SZ` properties fail structural validation.

Record the exact model name/version, access surface, date, sampling settings where exposed, and whether tools or web access were enabled. If the model is allowed to call the duplicate API itself, report that as a separate tool-enabled condition.

## Run layout

```text
submissions/
  2026-08-04-chatgpt-example/
    run.json
    problem-01.sgf
    problem-02.sgf
    problem-03.sgf
    problem-04.sgf
    problem-05.sgf
```

Copy `submissions/run.example.json` to `run.json` and preserve the model's first SGF output exactly. If you repair a problem, save it as a new, explicitly labeled run; do not silently replace the first attempt.

## Acceptance pipeline

```text
raw output
  → parse and structural validation
  → local exact/transformed duplicate check
  → GoProblems radius-2 and percentage check
  → expert life/death and tree review
  → rubric score
```

### Hard gates

A candidate is rejected before scoring if any of these is true:

- It is not parseable SGF.
- A structural validator error remains.
- It contains a root comment or written problem instruction.
- It does not explicitly declare `SZ[19]` at the root.
- The position or any required line is illegal.
- The claimed `RIGHT` outcome is false.
- A materially correct alternative is missing or marked wrong.
- It matches the local exact/transformed fingerprint of a reference.
- GoProblems returns any radius-2 solution-signature match.
- The top GoProblems percentage match is at least 90% under the default policy.

Rejected candidates receive 0 points but remain part of the run's acceptance-rate denominator.

### Manual-review band

A top percentage match of 80–89%, a local solution-shape overlap of 80% or more, or a strong visual resemblance is held for side-by-side review. The reviewer records why the tactical idea and construction are materially distinct before accepting it.

## Reporting

For each run, report:

- Accepted problems / 5 (primary reliability metric)
- Mean score across all five, counting rejected candidates as 0 (primary quality metric)
- Mean score among accepted candidates (conditional quality)
- Structural pass rate
- Originality pass rate
- Median manual review time

Do not rank models only by their best problem. The benchmark is intended to measure reliable creation.

## Repeated trials

For a serious comparison, run at least three independent five-problem trials per model. Keep prompts and tool access fixed within a condition. Report mean and range; do not pool repaired and unrepaired runs.

## Current limitation

The first version automates SGF structure, board legality checks, local transformed fingerprints, and GoProblems similarity queries. It does **not** prove life/death truth. Semantic correctness and completeness still require a competent Go reviewer (or a separately documented engine-assisted protocol). That distinction is intentional: parseability is not the same as a sound tsumego.
