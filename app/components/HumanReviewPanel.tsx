"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  isReviewMarkedBad,
  reviewPassesHumanGates,
  reviewProblemIsComplete,
  reviewProblemProgress,
  type ReviewProblemProgress,
} from "@/lib/review-progress";

export interface ReviewProblem {
  file: string;
  status: "pending" | "completed";
  valid: boolean | null;
  realistic: boolean | null;
  duplicate: boolean | null;
  wellPathed: boolean | null;
  estimatedDifficulty: string | null;
  quality: number | null;
  reviewedAt: string | null;
}

interface ReviewerRecord {
  reviewId: string;
  reviewerName: string;
  createdAt: string;
  updatedAt: string;
  problems: ReviewProblem[];
}

interface ReviewSession {
  runId: string;
  problemFiles: string[];
  difficultyOptions: string[];
  reviews: ReviewerRecord[];
}

interface ReviewLaunch {
  api: string;
  token: string;
}

interface ReviewDraft {
  valid: boolean;
  realistic: boolean;
  duplicate: boolean;
  wellPathed: boolean;
  estimatedDifficulty: string;
  quality: number | null;
}

function withoutUnneededRatings(draft: ReviewDraft): ReviewDraft {
  return reviewPassesHumanGates(draft)
    ? draft
    : { ...draft, estimatedDifficulty: "", quality: null };
}

export interface ReviewProgressSnapshot {
  runId: string;
  problems: Record<string, ReviewProblemProgress>;
  badProblems: string[];
}

interface HumanReviewPanelProps {
  runId: string;
  problemFile: string;
  automaticallyRejectedFiles: string[];
  onChooseProblem: (file: string) => void;
  onReviewProgressChange: (snapshot: ReviewProgressSnapshot | null) => void;
}

function launchFromLocation(): ReviewLaunch | null {
  const params = new URLSearchParams(window.location.search);
  if (params.get("review") !== "1") return null;
  const apiValue = params.get("reviewApi");
  const token = params.get("token");
  if (!apiValue || !token) return null;
  try {
    const api = new URL(apiValue);
    if (
      api.protocol !== "http:" ||
      !new Set(["127.0.0.1", "localhost"]).has(api.hostname)
    ) {
      return null;
    }
    return { api: api.origin, token };
  } catch {
    return null;
  }
}

function blankReviewProblem(file: string): ReviewProblem {
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
  };
}

export function markAllReviewProblemsInvalid(
  problems: readonly ReviewProblem[],
  reviewedAt: string,
): ReviewProblem[] {
  return problems.map((problem) => ({
    ...problem,
    status: "completed",
    valid: false,
    estimatedDifficulty: null,
    quality: null,
    reviewedAt,
  }));
}

export function findNextUnreviewedProblemFile(
  problems: ReviewProblem[],
  currentFile: string,
  automaticallyRejectedFiles: readonly string[],
): string | null {
  const rejected = new Set(automaticallyRejectedFiles);
  const currentIndex = problems.findIndex((problem) => problem.file === currentFile);
  const orderedProblems = currentIndex < 0
    ? problems
    : [
        ...problems.slice(currentIndex + 1),
        ...problems.slice(0, currentIndex),
      ];
  return orderedProblems.find(
    (problem) => reviewProblemProgress(problem) === "untouched" && !rejected.has(problem.file),
  )?.file ?? null;
}

function reviewProgressSnapshot(runId: string, review: ReviewerRecord): ReviewProgressSnapshot {
  return {
    runId,
    problems: Object.fromEntries(
      review.problems.map((problem) => [problem.file, reviewProblemProgress(problem)]),
    ),
    badProblems: review.problems
      .filter(isReviewMarkedBad)
      .map((problem) => problem.file),
  };
}

export function HumanReviewPanel({
  runId,
  problemFile,
  automaticallyRejectedFiles,
  onChooseProblem,
  onReviewProgressChange,
}: HumanReviewPanelProps) {
  const [launch, setLaunch] = useState<ReviewLaunch | null>(null);
  const [session, setSession] = useState<ReviewSession | null>(null);
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null);
  const [reviewerName, setReviewerName] = useState("");
  const [valid, setValid] = useState(true);
  const [realistic, setRealistic] = useState(true);
  const [duplicate, setDuplicate] = useState(false);
  const [wellPathed, setWellPathed] = useState(true);
  const [estimatedDifficulty, setEstimatedDifficulty] = useState("");
  const [quality, setQuality] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const activeReview = useMemo(
    () => session?.reviews.find((review) => review.reviewId === activeReviewId) ?? null,
    [activeReviewId, session],
  );
  const completed = activeReview?.problems.filter(reviewProblemIsComplete).length ?? 0;
  const difficultyRequired = reviewPassesHumanGates({
    valid,
    realistic,
    duplicate,
    wellPathed,
  });
  const nextUnreviewedProblemFile = activeReview
    ? findNextUnreviewedProblemFile(
        activeReview.problems,
        problemFile,
        automaticallyRejectedFiles,
      )
    : null;

  useEffect(() => {
    const parsed = launchFromLocation();
    if (!parsed) return;
    const launchTimer = window.setTimeout(() => setLaunch(parsed), 0);
    fetch(`${parsed.api}/session`, {
      headers: { Authorization: `Bearer ${parsed.token}` },
      cache: "no-store",
    })
      .then(async (response) => {
        const value = await response.json();
        if (!response.ok) throw new Error(value.error ?? "The review session could not be loaded.");
        return value as ReviewSession;
      })
      .then((value) => {
        setSession(value);
        const remembered = window.localStorage.getItem(`tsumego-review:${value.runId}`);
        if (remembered && value.reviews.some((review) => review.reviewId === remembered)) {
          setActiveReviewId(remembered);
        }
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "The review session could not be loaded.");
      });
    return () => window.clearTimeout(launchTimer);
  }, []);

  useEffect(() => {
    const record = activeReview?.problems.find((problem) => problem.file === problemFile);
    const draftTimer = window.setTimeout(() => {
      setValid(record?.valid ?? true);
      setRealistic(record?.realistic ?? true);
      setDuplicate(record?.duplicate ?? false);
      setWellPathed(record?.wellPathed ?? true);
      setEstimatedDifficulty(
        record && reviewPassesHumanGates(record)
          ? record.estimatedDifficulty ?? ""
          : "",
      );
      setQuality(
        record && reviewPassesHumanGates(record)
          ? record.quality ?? null
          : null,
      );
    }, 0);
    return () => window.clearTimeout(draftTimer);
  }, [activeReview, problemFile]);

  useEffect(() => {
    onReviewProgressChange(
      activeReview ? reviewProgressSnapshot(runId, activeReview) : null,
    );
  }, [activeReview, onReviewProgressChange, runId]);

  async function persist(review: ReviewerRecord) {
    if (!launch) throw new Error("The local review service is unavailable.");
    const response = await fetch(`${launch.api}/reviews/${review.reviewId}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${launch.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(review),
    });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error ?? "The review could not be saved.");
    setSession((current) => current ? { ...current, reviews: value.reviews } : current);
    if (value.warning) setMessage(`Saved. ${value.warning}`);
    return value.review as ReviewerRecord;
  }

  async function startReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !reviewerName.trim()) return;
    setSaving(true);
    setError("");
    try {
      const reviewId = crypto.randomUUID();
      const now = new Date().toISOString();
      const saved = await persist({
        reviewId,
        reviewerName: reviewerName.trim(),
        createdAt: now,
        updatedAt: now,
        problems: session.problemFiles.map(blankReviewProblem),
      });
      setActiveReviewId(saved.reviewId);
      window.localStorage.setItem(`tsumego-review:${session.runId}`, saved.reviewId);
      setReviewerName("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The reviewer record could not be created.");
    } finally {
      setSaving(false);
    }
  }

  async function autoSaveProblemReview(draft: ReviewDraft) {
    if (!activeReview || !session) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const now = new Date().toISOString();
      const normalizedDraft = withoutUnneededRatings(draft);
      const reviewComplete = reviewProblemIsComplete(normalizedDraft);
      const nextReview: ReviewerRecord = {
        ...activeReview,
        updatedAt: now,
        problems: activeReview.problems.map((problem) =>
          problem.file === problemFile
            ? {
                file: problem.file,
                status: reviewComplete ? "completed" : "pending",
                valid: normalizedDraft.valid,
                realistic: normalizedDraft.realistic,
                duplicate: normalizedDraft.duplicate,
                wellPathed: normalizedDraft.wellPathed,
                estimatedDifficulty: normalizedDraft.estimatedDifficulty || null,
                quality: normalizedDraft.quality,
                reviewedAt: reviewComplete ? now : null,
              }
            : problem,
        ),
      };
      onReviewProgressChange(reviewProgressSnapshot(runId, nextReview));
      const saved = await persist(nextReview);
      setActiveReviewId(saved.reviewId);
      setMessage("Saved automatically.");
    } catch (reason) {
      onReviewProgressChange(reviewProgressSnapshot(runId, activeReview));
      setError(reason instanceof Error ? reason.message : "The review change could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  function chooseReviewer(reviewId: string) {
    setActiveReviewId(reviewId);
    if (session) window.localStorage.setItem(`tsumego-review:${session.runId}`, reviewId);
  }

  function nextPendingProblem() {
    if (nextUnreviewedProblemFile) onChooseProblem(nextUnreviewedProblemFile);
  }

  async function markEveryProblemInvalid() {
    if (!activeReview) return;
    const problemCount = activeReview.problems.length;
    const confirmed = window.confirm(
      `Mark all ${problemCount} problems invalid? This will clear any existing difficulty and quality ratings for this reviewer.`,
    );
    if (!confirmed) return;

    setSaving(true);
    setError("");
    setMessage("");
    try {
      const now = new Date().toISOString();
      const nextReview: ReviewerRecord = {
        ...activeReview,
        updatedAt: now,
        problems: markAllReviewProblemsInvalid(activeReview.problems, now),
      };
      onReviewProgressChange(reviewProgressSnapshot(runId, nextReview));
      const saved = await persist(nextReview);
      setActiveReviewId(saved.reviewId);
      setValid(false);
      setEstimatedDifficulty("");
      setQuality(null);
      setMessage(`All ${problemCount} problems marked invalid.`);
    } catch (reason) {
      onReviewProgressChange(reviewProgressSnapshot(runId, activeReview));
      setMessage("");
      setError(reason instanceof Error ? reason.message : "The bulk review change could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (!launch) return null;

  if (error && !session) {
    return <div className="human-review-panel review-session-error">{error}</div>;
  }

  if (!session || session.runId !== runId) return null;

  return (
    <section className="human-review-panel" aria-labelledby="human-review-title">
      <header className="human-review-header">
        <div>
          <span className="panel-label">LOCAL HUMAN REVIEW</span>
          <strong id="human-review-title">
            {activeReview ? activeReview.reviewerName : "Choose a reviewer"}
          </strong>
        </div>
        {activeReview && (
          <div className="review-progress" aria-label={`${completed} of ${activeReview.problems.length} reviewed`}>
            <strong>{completed}/{activeReview.problems.length}</strong>
            <span>reviewed</span>
          </div>
        )}
      </header>

      {!activeReview ? (
        <div className="reviewer-chooser">
          {session.reviews.length > 0 && (
            <div className="existing-reviewers">
              {session.reviews.map((review) => {
                const count = review.problems.filter(reviewProblemIsComplete).length;
                return (
                  <button type="button" key={review.reviewId} onClick={() => chooseReviewer(review.reviewId)}>
                    <strong>{review.reviewerName}</strong>
                    <span>{count}/{review.problems.length}</span>
                  </button>
                );
              })}
            </div>
          )}
          <form className="new-reviewer-form" onSubmit={startReview}>
            <label>
              <span>New reviewer</span>
              <input
                value={reviewerName}
                onChange={(event) => setReviewerName(event.target.value)}
                maxLength={100}
                placeholder="Reviewer name"
              />
            </label>
            <button type="submit" disabled={!reviewerName.trim() || saving}>
              Start review
            </button>
          </form>
        </div>
      ) : (
        <div className="review-form">
          <div className="review-checkboxes">
            <label>
              <input
                type="checkbox"
                checked={valid}
                disabled={saving}
                onChange={(event) => {
                  const nextValid = event.target.checked;
                  const nextDraft = withoutUnneededRatings({
                    valid: nextValid,
                    realistic,
                    duplicate,
                    wellPathed,
                    estimatedDifficulty,
                    quality,
                  });
                  setValid(nextValid);
                  setEstimatedDifficulty(nextDraft.estimatedDifficulty);
                  setQuality(nextDraft.quality);
                  void autoSaveProblemReview(nextDraft);
                }}
              />
              <span>Valid problem</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={realistic}
                disabled={saving}
                onChange={(event) => {
                  const nextRealistic = event.target.checked;
                  const nextDraft = withoutUnneededRatings({
                    valid,
                    realistic: nextRealistic,
                    duplicate,
                    wellPathed,
                    estimatedDifficulty,
                    quality,
                  });
                  setRealistic(nextRealistic);
                  setEstimatedDifficulty(nextDraft.estimatedDifficulty);
                  setQuality(nextDraft.quality);
                  void autoSaveProblemReview(nextDraft);
                }}
              />
              <span>Realistic position</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={duplicate}
                disabled={saving}
                onChange={(event) => {
                  const nextDuplicate = event.target.checked;
                  const nextDraft = withoutUnneededRatings({
                    valid,
                    realistic,
                    duplicate: nextDuplicate,
                    wellPathed,
                    estimatedDifficulty,
                    quality,
                  });
                  setDuplicate(nextDuplicate);
                  setEstimatedDifficulty(nextDraft.estimatedDifficulty);
                  setQuality(nextDraft.quality);
                  void autoSaveProblemReview(nextDraft);
                }}
              />
              <span>Duplicate</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={wellPathed}
                disabled={saving}
                onChange={(event) => {
                  const nextWellPathed = event.target.checked;
                  const nextDraft = withoutUnneededRatings({
                    valid,
                    realistic,
                    duplicate,
                    wellPathed: nextWellPathed,
                    estimatedDifficulty,
                    quality,
                  });
                  setWellPathed(nextWellPathed);
                  setEstimatedDifficulty(nextDraft.estimatedDifficulty);
                  setQuality(nextDraft.quality);
                  void autoSaveProblemReview(nextDraft);
                }}
              />
              <span>Well pathed</span>
            </label>
          </div>

          <label className="review-difficulty">
            <span>Estimated difficulty · required only when all checks pass</span>
            <select
              value={estimatedDifficulty}
              onChange={(event) => {
                const nextDifficulty = event.target.value;
                setEstimatedDifficulty(nextDifficulty);
                void autoSaveProblemReview({
                  valid,
                  realistic,
                  duplicate,
                  wellPathed,
                  estimatedDifficulty: nextDifficulty,
                  quality,
                });
              }}
              disabled={!difficultyRequired || saving}
            >
              <option value="">Select human-estimated range</option>
              {session.difficultyOptions.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>

          <fieldset className="quality-rating" disabled={!difficultyRequired || saving}>
            <legend>Problem quality · only when all checks pass</legend>
            <div role="radiogroup" aria-label="Problem quality from one to five stars">
              {[1, 2, 3, 4, 5].map((rating) => (
                <button
                  type="button"
                  key={rating}
                  className={quality !== null && rating <= quality ? "selected" : ""}
                  onClick={() => {
                    setQuality(rating);
                    void autoSaveProblemReview({
                      valid,
                      realistic,
                      duplicate,
                      wellPathed,
                      estimatedDifficulty,
                      quality: rating,
                    });
                  }}
                  disabled={!difficultyRequired || saving}
                  role="radio"
                  aria-checked={quality === rating}
                  aria-label={`${rating} star${rating === 1 ? "" : "s"}`}
                >
                  ★
                </button>
              ))}
            </div>
          </fieldset>

          <div className="review-actions">
            <span className="review-autosave-status" role="status">
              {saving ? "Saving…" : message}
            </span>
            <button
              type="button"
              onClick={nextPendingProblem}
              disabled={saving || !nextUnreviewedProblemFile}
            >
              Next pending
            </button>
            <button
              type="button"
              className="review-all-invalid"
              onClick={() => void markEveryProblemInvalid()}
              disabled={saving}
            >
              Mark all invalid
            </button>
            <button
              type="button"
              className="review-switch"
              onClick={() => setActiveReviewId(null)}
              disabled={saving}
            >
              Switch reviewer
            </button>
            {error && <span className="review-error" role="alert">{error}</span>}
          </div>
        </div>
      )}
    </section>
  );
}
