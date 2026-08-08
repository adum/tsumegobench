import assert from "node:assert/strict";
import test from "node:test";

import {
  findNextUnreviewedProblemFile,
  markAllReviewProblemsInvalid,
  type ReviewProblem,
} from "../app/components/HumanReviewPanel";
import {
  aggregateReviewProgress,
  difficultyCappedHumanScore,
  isReviewMarkedBad,
  problemPassesHumanReview,
  reviewProblemIsComplete,
  reviewedProblemDifficulty,
  reviewProblemProgress,
} from "../lib/review-progress";

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

  assert.equal(isReviewMarkedBad(untouched), false);
  assert.equal(isReviewMarkedBad(approved), false);
  assert.equal(isReviewMarkedBad({ ...approved, valid: false }), true);
  assert.equal(isReviewMarkedBad({ ...approved, realistic: false }), true);
  assert.equal(isReviewMarkedBad({ ...approved, duplicate: true }), true);
  assert.equal(isReviewMarkedBad({ ...approved, wellPathed: false }), true);
});

test("rejected problems complete without a rating while passing problems require one", () => {
  const passingGates = reviewProblem("problem-01.sgf", {
    valid: true,
    realistic: true,
    duplicate: false,
    wellPathed: true,
  });

  assert.equal(reviewProblemIsComplete(passingGates), false);
  assert.equal(
    reviewProblemIsComplete({ ...passingGates, estimatedDifficulty: "5-9 kyu" }),
    true,
  );
  assert.equal(reviewProblemIsComplete({ ...passingGates, valid: false }), true);
  assert.equal(reviewProblemIsComplete({ ...passingGates, realistic: false }), true);
  assert.equal(reviewProblemIsComplete({ ...passingGates, duplicate: true }), true);
  assert.equal(reviewProblemIsComplete({ ...passingGates, wellPathed: false }), true);
});

test("bulk rejection marks every problem invalid and clears human ratings", () => {
  const problems = [
    reviewProblem("problem-01.sgf", {
      status: "completed",
      valid: true,
      realistic: true,
      duplicate: false,
      wellPathed: true,
      estimatedDifficulty: "5-9 kyu",
      quality: 5,
      reviewedAt: "2026-08-07T01:00:00Z",
    }),
    reviewProblem("problem-02.sgf"),
  ];

  const rejected = markAllReviewProblemsInvalid(problems, "2026-08-07T02:00:00Z");

  assert.notEqual(rejected, problems);
  assert.equal(problems[0].valid, true);
  assert.deepEqual(
    rejected.map(({ file, status, valid, estimatedDifficulty, quality, reviewedAt }) => ({
      file,
      status,
      valid,
      estimatedDifficulty,
      quality,
      reviewedAt,
    })),
    ["problem-01.sgf", "problem-02.sgf"].map((file) => ({
      file,
      status: "completed",
      valid: false,
      estimatedDifficulty: null,
      quality: null,
      reviewedAt: "2026-08-07T02:00:00Z",
    })),
  );
});

test("saved partial reviews remain visibly in progress", () => {
  const untouched = reviewProblem("problem-01.sgf");
  const started = reviewProblem("problem-01.sgf", { duplicate: false });
  const completed = reviewProblem("problem-01.sgf", {
    valid: true,
    realistic: true,
    duplicate: false,
    wellPathed: true,
    estimatedDifficulty: "5-9 kyu",
    quality: null,
  });

  assert.equal(reviewProblemProgress(untouched), "untouched");
  assert.equal(reviewProblemProgress(started), "started");
  assert.equal(reviewProblemProgress(completed), "completed");
  assert.equal(aggregateReviewProgress([untouched, started]), "started");
  assert.equal(aggregateReviewProgress([started, completed]), "completed");
});

test("human pass requires every gate plus a difficulty rating", () => {
  const passing = reviewProblem("problem-01.sgf", {
    valid: true,
    realistic: true,
    duplicate: false,
    wellPathed: true,
    estimatedDifficulty: "5-9 kyu",
  });

  assert.equal(problemPassesHumanReview([]), false);
  assert.equal(problemPassesHumanReview([passing]), true);
  assert.equal(problemPassesHumanReview([{ ...passing, estimatedDifficulty: null }]), false);
  assert.equal(problemPassesHumanReview([passing, { ...passing, valid: false }]), false);
  assert.equal(problemPassesHumanReview([passing, { ...passing, realistic: false }]), false);
  assert.equal(problemPassesHumanReview([passing, { ...passing, wellPathed: false }]), false);
  assert.equal(problemPassesHumanReview([passing, { ...passing, duplicate: true }]), false);
});

test("human score caps the two easiest ranges and leaves harder problems uncapped", () => {
  function passingProblem(difficulty: string | null) {
    return {
      reviews: [
        reviewProblem("problem.sgf", {
          status: "completed",
          valid: true,
          realistic: true,
          duplicate: false,
          wellPathed: true,
          estimatedDifficulty: difficulty,
        }),
      ],
    };
  }

  const score = difficultyCappedHumanScore([
    ...Array.from({ length: 5 }, () => passingProblem("20-30 kyu")),
    ...Array.from({ length: 3 }, () => passingProblem("10-19 kyu")),
    ...Array.from({ length: 2 }, () => passingProblem("5-9 kyu")),
    passingProblem("2-3 dan"),
    passingProblem("4 dan or harder"),
    passingProblem(null),
  ]);

  assert.equal(score.passingProblems, 12);
  assert.equal(score.creditedProblems, 8);
  assert.deepEqual(score.counts, {
    twentyToThirtyKyu: 5,
    tenToNineteenKyu: 3,
    fiveKyuOrHarder: 4,
    unrated: 0,
  });
});

test("difficulty disagreements use the easiest completed human rating", () => {
  const base = reviewProblem("problem-01.sgf", {
    valid: true,
    realistic: true,
    duplicate: false,
    wellPathed: true,
  });

  assert.equal(
    reviewedProblemDifficulty([
      { ...base, estimatedDifficulty: "2-3 dan" },
      { ...base, estimatedDifficulty: "10-19 kyu" },
    ]),
    "10-19 kyu",
  );
  assert.equal(
    reviewedProblemDifficulty([
      { ...base, estimatedDifficulty: "5-9 kyu" },
      { ...base, estimatedDifficulty: null },
    ]),
    "5-9 kyu",
  );
});
