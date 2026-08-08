export interface RunReviewProgress {
  completed: number;
  remaining: number;
  required: number;
}

interface RunWithReviewStatus {
  status: string;
  summary: {
    humanReviewPending?: number;
  };
  humanReviews?: {
    completedProblemReviews?: number;
    reviewers?: Array<{
      completed: number;
    }>;
  };
}

export function indexedRunReviewProgress(
  record: RunWithReviewStatus,
): RunReviewProgress {
  const required = Math.max(0, record.summary.humanReviewPending ?? 0);
  const completed = Math.max(
    0,
    record.humanReviews?.completedProblemReviews ?? 0,
    ...(record.humanReviews?.reviewers?.map((reviewer) => reviewer.completed) ?? []),
  );

  return {
    completed,
    remaining: Math.max(0, required - completed),
    required,
  };
}

export function displayRunStatus(
  record: RunWithReviewStatus,
  reviewProgress: RunReviewProgress = indexedRunReviewProgress(record),
) {
  return record.status === "needs_human_review" &&
    reviewProgress.required > 0 &&
    reviewProgress.remaining === 0
    ? "reviewed"
    : record.status;
}
