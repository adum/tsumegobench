# Evaluation rubric

Apply this 100-point rubric only after a candidate passes every hard gate in `docs/benchmark-spec.md`. Record short evidence for each category; do not score from visual appeal alone.

## 1. Life-and-death correctness — 30 points

- **27–30:** Intended result is unambiguous and correct under best resistance; clean life/death, seki, and ko status are classified properly.
- **20–26:** Correct central idea with a minor outcome-label or explanatory weakness that does not change accepted moves.
- **1–19:** Substantial uncertainty or context dependence.
- **0 / reject:** A `RIGHT` line is false, a supposedly losing line succeeds, or legality fails.

## 2. Solution-tree completeness — 25 points

- **22–25:** Covers all materially correct solver choices and continuations, strongest materially distinct defenses, and plausible level-appropriate mistakes. Correct and refutation paths stop at natural, unambiguous endpoints without premature endings or routine cleanup.
- **16–21:** Core coverage is sound, but one low-value response is thin or an endpoint is slightly early or late without making the result uncertain.
- **1–15:** Important defensive or refutation ideas are underexplored, or several paths stop before demonstrating their result or continue well beyond it.
- **0 / reject:** A materially correct alternative is omitted or marked wrong; a necessary best defense is missing; or a path ends before its claimed correct or refuted result is established.

## 3. Construction and canonical style — 20 points

- **18–20:** Local, realistic, visually economical, clear without special instructions, and shaped like a useful classical problem.
- **13–17:** Solid but has a few excess stones, awkward presentation, or an unclear target group.
- **1–12:** Contrived, noisy, ambiguous, or dependent on artificial controls.

## 4. Pedagogical value and difficulty fit — 15 points

- **13–15:** Has a recognizable lesson, an instructive wrong idea, and a fair difficulty within the 30 kyu–1 dan target range.
- **9–12:** Useful practice but obvious, unevenly graded, or weakly differentiated.
- **1–8:** Little beyond a one-move spot-the-point exercise or an opaque reading contest.

## 5. Originality — 10 points

- **9–10:** No database warning; distinct shape and tactical construction even when using a classical motif.
- **6–8:** Passes gates but falls in an 80–89% similarity/manual-review band; reviewer explains the material difference.
- **1–5:** Suspicious resemblance despite technically passing automated thresholds.
- **0 / reject:** Exact/transformed local match, any radius-2 GoProblems signature match, or ≥90% default percentage match.

## Review record

```text
Run / problem:
Reviewer and Go rank:
Structural gate: PASS / FAIL
Local duplicate gate: PASS / FAIL
Remote signature gate: PASS / FAIL / NOT RUN
Correctness (30):
Tree completeness (25):
Canonical style (20):
Pedagogical fit (15):
Originality (10):
Total (100):
Evidence / notes:
```
