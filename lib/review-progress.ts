export type ReviewProblemProgress = "untouched" | "started" | "completed";

export interface ReviewProgressFields {
  status?: "pending" | "completed";
  valid?: boolean | null;
  realistic?: boolean | null;
  duplicate?: boolean | null;
  wellPathed?: boolean | null;
  estimatedDifficulty?: string | null;
  quality?: number | null;
}

export function reviewProblemProgress(
  problem: ReviewProgressFields,
): ReviewProblemProgress {
  if (problem.status === "completed") return "completed";
  if (
    typeof problem.valid === "boolean" ||
    typeof problem.realistic === "boolean" ||
    typeof problem.duplicate === "boolean" ||
    typeof problem.wellPathed === "boolean" ||
    problem.estimatedDifficulty != null ||
    problem.quality != null
  ) {
    return "started";
  }
  return "untouched";
}

export function aggregateReviewProgress(
  reviews: readonly ReviewProgressFields[],
): ReviewProblemProgress {
  const progress = reviews.map(reviewProblemProgress);
  if (progress.includes("completed")) return "completed";
  if (progress.includes("started")) return "started";
  return "untouched";
}

export function isReviewMarkedBad(problem: ReviewProgressFields): boolean {
  return (
    problem.valid === false ||
    problem.realistic === false ||
    problem.duplicate === true ||
    problem.wellPathed === false
  );
}
