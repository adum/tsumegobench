import assert from "node:assert/strict";
import test from "node:test";

import {
  displayRunStatus,
  indexedRunReviewProgress,
} from "../lib/run-status";

function runStatusFixture(
  completed: number,
  required = 10,
  status = "needs_human_review",
) {
  return {
    status,
    summary: { humanReviewPending: required },
    humanReviews: {
      completedProblemReviews: completed,
      reviewers: [{ completed }],
    },
  };
}

test("completed human review changes the display status to reviewed", () => {
  const run = runStatusFixture(10);

  assert.deepEqual(indexedRunReviewProgress(run), {
    completed: 10,
    remaining: 0,
    required: 10,
  });
  assert.equal(displayRunStatus(run), "reviewed");
});

test("partially reviewed runs still need human review", () => {
  assert.equal(displayRunStatus(runStatusFixture(7)), "needs_human_review");
});

test("review completion does not conceal a failed run", () => {
  assert.equal(displayRunStatus(runStatusFixture(10, 10, "failed")), "failed");
});
