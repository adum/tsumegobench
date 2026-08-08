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

export const HUMAN_DIFFICULTY_BANDS = [
  "20-30 kyu",
  "10-19 kyu",
  "5-9 kyu",
  "1-4 kyu",
  "about 1 dan",
  "2-3 dan",
  "4 dan or harder",
] as const;

export type HumanDifficultyBand = (typeof HUMAN_DIFFICULTY_BANDS)[number];

export interface DifficultyScoredProblem {
  reviews?: readonly ReviewProgressFields[];
}

export interface DifficultyCappedHumanScore {
  creditedProblems: number;
  passingProblems: number;
  counts: {
    twentyToThirtyKyu: number;
    tenToNineteenKyu: number;
    fiveKyuOrHarder: number;
    unrated: number;
  };
}

const DIFFICULTY_INDEX = new Map<string, number>(
  HUMAN_DIFFICULTY_BANDS.map((band, index) => [band, index]),
);

export const HUMAN_DIFFICULTY_CREDIT_CAPS = {
  twentyToThirtyKyu: 2,
  tenToNineteenKyu: 2,
} as const;

export function isReviewMarkedBad(problem: ReviewProgressFields): boolean {
  return (
    problem.valid === false ||
    problem.realistic === false ||
    problem.duplicate === true ||
    problem.wellPathed === false
  );
}

export function reviewPassesHumanGates(problem: ReviewProgressFields): boolean {
  return (
    problem.valid === true &&
    problem.realistic === true &&
    problem.duplicate === false &&
    problem.wellPathed === true
  );
}

export function reviewProblemIsComplete(problem: ReviewProgressFields): boolean {
  if (isReviewMarkedBad(problem)) return true;
  return (
    reviewPassesHumanGates(problem) &&
    typeof problem.estimatedDifficulty === "string" &&
    DIFFICULTY_INDEX.has(problem.estimatedDifficulty)
  );
}

export function reviewProblemProgress(
  problem: ReviewProgressFields,
): ReviewProblemProgress {
  if (reviewProblemIsComplete(problem)) return "completed";
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

export function problemPassesHumanReview(
  reviews: readonly ReviewProgressFields[],
): boolean {
  const completedReviews = reviews.filter(reviewProblemIsComplete);

  return (
    completedReviews.length > 0 &&
    completedReviews.every(reviewPassesHumanGates)
  );
}

export function reviewedProblemDifficulty(
  reviews: readonly ReviewProgressFields[],
): HumanDifficultyBand | null {
  if (!problemPassesHumanReview(reviews)) return null;

  const completedReviews = reviews.filter(reviewProblemIsComplete);
  const difficultyIndexes = completedReviews.map((review) =>
    typeof review.estimatedDifficulty === "string"
      ? DIFFICULTY_INDEX.get(review.estimatedDifficulty)
      : undefined,
  );
  if (difficultyIndexes.some((index) => index === undefined)) return null;

  // Multiple reviewers can disagree. Use the easiest submitted band so a
  // disagreement can never inflate a model's credited score.
  const easiestIndex = Math.min(...(difficultyIndexes as number[]));
  return HUMAN_DIFFICULTY_BANDS[easiestIndex];
}

export function difficultyCappedHumanScore(
  problems: readonly DifficultyScoredProblem[],
): DifficultyCappedHumanScore {
  const counts = {
    twentyToThirtyKyu: 0,
    tenToNineteenKyu: 0,
    fiveKyuOrHarder: 0,
    unrated: 0,
  };
  let passingProblems = 0;

  for (const problem of problems) {
    const reviews = problem.reviews ?? [];
    if (!problemPassesHumanReview(reviews)) continue;
    passingProblems += 1;

    const difficulty = reviewedProblemDifficulty(reviews);
    if (difficulty === "20-30 kyu") counts.twentyToThirtyKyu += 1;
    else if (difficulty === "10-19 kyu") counts.tenToNineteenKyu += 1;
    else if (difficulty) counts.fiveKyuOrHarder += 1;
    else counts.unrated += 1;
  }

  const creditedProblems =
    Math.min(
      HUMAN_DIFFICULTY_CREDIT_CAPS.twentyToThirtyKyu,
      counts.twentyToThirtyKyu,
    ) +
    Math.min(
      HUMAN_DIFFICULTY_CREDIT_CAPS.tenToNineteenKyu,
      counts.tenToNineteenKyu,
    ) +
    counts.fiveKyuOrHarder;

  return { creditedProblems, passingProblems, counts };
}
