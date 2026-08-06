"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

interface ReviewProblem {
  file: string;
  status: "pending" | "completed";
  valid: boolean | null;
  realistic: boolean | null;
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
  estimatedDifficulty: string;
  quality: number | null;
}

export type ReviewProblemProgress = "untouched" | "started" | "completed";

export interface ReviewProgressSnapshot {
  runId: string;
  problems: Record<string, ReviewProblemProgress>;
}

interface HumanReviewPanelProps {
  runId: string;
  problemFile: string;
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
    estimatedDifficulty: null,
    quality: null,
    reviewedAt: null,
  };
}

function problemProgress(problem: ReviewProblem): ReviewProblemProgress {
  if (problem.status === "completed") return "completed";
  if (
    problem.valid !== null ||
    problem.realistic !== null ||
    problem.estimatedDifficulty !== null ||
    problem.quality !== null
  ) {
    return "started";
  }
  return "untouched";
}

function reviewProgressSnapshot(runId: string, review: ReviewerRecord): ReviewProgressSnapshot {
  return {
    runId,
    problems: Object.fromEntries(
      review.problems.map((problem) => [problem.file, problemProgress(problem)]),
    ),
  };
}

export function HumanReviewPanel({
  runId,
  problemFile,
  onChooseProblem,
  onReviewProgressChange,
}: HumanReviewPanelProps) {
  const [launch, setLaunch] = useState<ReviewLaunch | null>(null);
  const [session, setSession] = useState<ReviewSession | null>(null);
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null);
  const [reviewerName, setReviewerName] = useState("");
  const [valid, setValid] = useState(false);
  const [realistic, setRealistic] = useState(false);
  const [estimatedDifficulty, setEstimatedDifficulty] = useState("");
  const [quality, setQuality] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const activeReview = useMemo(
    () => session?.reviews.find((review) => review.reviewId === activeReviewId) ?? null,
    [activeReviewId, session],
  );
  const completed = activeReview?.problems.filter((problem) => problem.status === "completed").length ?? 0;

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
      setValid(record?.valid ?? false);
      setRealistic(record?.realistic ?? false);
      setEstimatedDifficulty(record?.estimatedDifficulty ?? "");
      setQuality(record?.quality ?? null);
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
      const isComplete =
        draft.quality !== null &&
        (!draft.valid || Boolean(draft.estimatedDifficulty));
      const nextReview: ReviewerRecord = {
        ...activeReview,
        updatedAt: now,
        problems: activeReview.problems.map((problem) =>
          problem.file === problemFile
            ? {
                file: problem.file,
                status: isComplete ? "completed" : "pending",
                valid: draft.valid,
                realistic: draft.realistic,
                estimatedDifficulty: draft.valid ? draft.estimatedDifficulty || null : null,
                quality: draft.quality,
                reviewedAt: isComplete ? now : null,
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
    const pending = activeReview?.problems.find((problem) => problem.status === "pending");
    if (pending) onChooseProblem(pending.file);
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
                const count = review.problems.filter((problem) => problem.status === "completed").length;
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
                  const nextDifficulty = nextValid ? estimatedDifficulty : "";
                  setValid(nextValid);
                  setEstimatedDifficulty(nextDifficulty);
                  void autoSaveProblemReview({
                    valid: nextValid,
                    realistic,
                    estimatedDifficulty: nextDifficulty,
                    quality,
                  });
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
                  setRealistic(nextRealistic);
                  void autoSaveProblemReview({
                    valid,
                    realistic: nextRealistic,
                    estimatedDifficulty,
                    quality,
                  });
                }}
              />
              <span>Realistic position</span>
            </label>
          </div>

          <label className="review-difficulty">
            <span>Estimated difficulty</span>
            <select
              value={estimatedDifficulty}
              onChange={(event) => {
                const nextDifficulty = event.target.value;
                setEstimatedDifficulty(nextDifficulty);
                void autoSaveProblemReview({
                  valid,
                  realistic,
                  estimatedDifficulty: nextDifficulty,
                  quality,
                });
              }}
              disabled={!valid || saving}
            >
              <option value="">Select difficulty</option>
              {session.difficultyOptions.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>

          <fieldset className="quality-rating">
            <legend>Problem quality</legend>
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
                      estimatedDifficulty,
                      quality: rating,
                    });
                  }}
                  disabled={saving}
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
              {saving ? "Saving…" : message || "Changes save automatically"}
            </span>
            <button
              type="button"
              onClick={nextPendingProblem}
              disabled={saving || completed >= activeReview.problems.length}
            >
              Next pending
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
