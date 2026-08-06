import assert from "node:assert/strict";
import test from "node:test";

import {
  findNextUnreviewedProblemFile,
  isProblemMarkedBad,
  type ReviewProblem,
} from "../app/components/HumanReviewPanel";

function reviewProblem(
  file: string,
  overrides: Partial<ReviewProblem> = {},
): ReviewProblem {
  return {
    file,
    status: "pending",
    valid: null,
    realistic: null,
    duplicate: null,
    wellPathed: null,
    estimatedDifficulty: null,
    quality: null,
    reviewedAt: null,
    ...overrides,
  };
}

test("next pending skips touched and automatically rejected problems", () => {
  const problems = [
    reviewProblem("problem-01.sgf", { status: "completed", valid: true }),
    reviewProblem("problem-02.sgf"),
    reviewProblem("problem-03.sgf", { quality: 2 }),
    reviewProblem("problem-04.sgf"),
  ];

  assert.equal(
    findNextUnreviewedProblemFile(problems, "problem-01.sgf", ["problem-02.sgf"]),
    "problem-04.sgf",
  );
});

test("next pending wraps around without selecting the current problem", () => {
  const problems = [
    reviewProblem("problem-01.sgf"),
    reviewProblem("problem-02.sgf", { realistic: true }),
    reviewProblem("problem-03.sgf"),
  ];

  assert.equal(
    findNextUnreviewedProblemFile(problems, "problem-03.sgf", []),
    "problem-01.sgf",
  );
  assert.equal(
    findNextUnreviewedProblemFile([reviewProblem("problem-01.sgf")], "problem-01.sgf", []),
    null,
  );
});

test("all four human review checkboxes can mark a problem bad", () => {
  const untouched = reviewProblem("problem-01.sgf");
  const approved = reviewProblem("problem-01.sgf", {
    valid: true,
    realistic: true,
    duplicate: false,
    wellPathed: true,
  });

  assert.equal(isProblemMarkedBad(untouched), false);
  assert.equal(isProblemMarkedBad(approved), false);
  assert.equal(isProblemMarkedBad({ ...approved, valid: false }), true);
  assert.equal(isProblemMarkedBad({ ...approved, realistic: false }), true);
  assert.equal(isProblemMarkedBad({ ...approved, duplicate: true }), true);
  assert.equal(isProblemMarkedBad({ ...approved, wellPathed: false }), true);
});
