"use client";

import { useCallback, useEffect, useState } from "react";
import runData from "../data/runs.generated.json";
import { GoBoard } from "./GoBoard";
import {
  HumanReviewPanel,
  type ReviewProgressSnapshot,
} from "./HumanReviewPanel";
import { ProblemThumbnail } from "./ProblemThumbnail";
import { SolutionTree } from "./SolutionTree";
import {
  aggregateReviewProgress,
  difficultyCappedHumanScore,
  isReviewMarkedBad,
  reviewProblemIsComplete,
  reviewProblemProgress,
  type ReviewProblemProgress,
} from "@/lib/review-progress";
import { formatDurationSeconds } from "@/lib/format-duration";
import {
  collectRightNodes,
  getBoardSize,
  getMove,
  getPath,
  getProblemStats,
  hasControlTag,
  parseSgf,
  pointToHuman,
  visibleComment,
  walkSgf,
  type SgfNode,
} from "@/lib/sgf";

type CheckStatus = "pass" | "fail" | "warning" | "not_run" | "needs_human_review";

interface RunCheck {
  id: string;
  status: CheckStatus;
  message: string;
}

interface GeneratedProblem {
  file: string;
  targetDifficulty: string;
  playerColor: "black" | "white" | null;
  status: "failed" | "incomplete" | "needs_human_review";
  automatedGate: "pass" | "fail" | "incomplete";
  sgf: string | null;
  validation: {
    valid: boolean;
    issues: Array<{ severity: "error" | "warning"; code: string; message: string }>;
    stats: {
      nodeCount: number;
      maxDepth: number;
      rightCount: number;
      setupStoneCount: number;
      variationPoints: number;
    } | null;
  };
  originality: {
    status: "pass" | "fail" | "manual_review" | "not_run";
    builtInSetupMatch?: { id: string; label: string } | null;
    exactLocalMatch: { id: number; sourceUrl: string } | null;
    closestLocalShape: { id: number; sourceUrl: string; percentage: number } | null;
    peerExactMatches: string[];
    peerShapeMatches: Array<{ file: string; percentage: number }>;
    remote: {
      status: "pass" | "fail" | "manual_review" | "not_run" | "error";
      radiusTwoMatches: Array<{ id: number }>;
      topPercentage: number | null;
      topMatchId: number | null;
      error: string | null;
    };
  };
  human: {
    status: "pending" | "accepted" | "rejected";
    estimatedDifficulty: string | null;
    notes: string;
  } | null;
  reviews?: Array<{
    reviewId: string;
    reviewerName: string;
    status: "pending" | "completed";
    valid: boolean | null;
    realistic: boolean | null;
    duplicate?: boolean | null;
    wellPathed?: boolean | null;
    estimatedDifficulty: string | null;
    quality: number | null;
    reviewedAt: string | null;
  }>;
}

interface BenchmarkRun {
  runId: string;
  status: "failed" | "incomplete" | "needs_human_review";
  createdAt: string;
  completedAt: string | null;
  model: {
    provider: string;
    name: string;
    reasoningEffort: string | null;
  };
  harness: {
    name: string;
    version: string | null;
    exitCode: number | null;
    durationSeconds: number | null;
  };
  condition: {
    remoteDuplicateEvaluation?: boolean;
  };
  originalityTool?: {
    queryLimit: number;
    queriesUsed: number;
    queriesRemaining: number;
    quotaExceeded: number;
    remoteCacheHits: number;
    results: {
      clear: number;
      review: number;
      duplicate: number;
      invalid: number;
      unavailable: number;
    };
  } | null;
  summary: {
    expectedProblems?: number;
    filesFound?: number;
    structuralPassed: number;
    originalityPassed: number;
    automatedGatePassed: number;
    failedProblems: number;
    incompleteProblems: number;
    humanReviewPending: number;
    failedRunChecks: number;
  };
  runChecks?: RunCheck[];
  humanReviews?: {
    completedProblemReviews: number;
    reviewers: Array<{
      completed: number;
      total: number;
    }>;
  };
  problems: GeneratedProblem[];
}

const runs = runData as BenchmarkRun[];

function humanDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("en", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(date);
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

function effortLabel(effort: string | null) {
  return `${effort?.replaceAll("_", " ") ?? "default"} effort`;
}

export function compactModelName(name: string) {
  return name.split("/").filter(Boolean).at(-1) ?? name;
}

function providerLabel(provider: string) {
  if (provider === "openai") return "OpenAI";
  if (provider === "anthropic") return "Anthropic";
  if (provider === "xai") return "xAI";
  if (provider === "opencode") return "OpenCode";
  return provider;
}

const providerIconSources: Record<string, string> = {
  openai: "/provider-icons/openai.svg",
  anthropic: "/provider-icons/anthropic.svg",
  xai: "/provider-icons/xai.svg",
  opencode: "/provider-icons/opencode.svg",
};

function providerInitials(provider: string) {
  if (provider === "openai") return "OA";
  if (provider === "anthropic") return "A";
  if (provider === "xai") return "xAI";
  if (provider === "opencode") return "OC";
  return provider.replace(/[^a-z0-9]/gi, "").slice(0, 2).toUpperCase() || "?";
}

function ProviderMark({ provider }: { provider: string }) {
  const source = providerIconSources[provider];

  return (
    <span
      className={`run-provider-mark${source ? "" : " fallback"}`}
      aria-label={`${providerLabel(provider)} model lab`}
      role="img"
      title={providerLabel(provider)}
    >
      <span className="run-provider-initials" aria-hidden="true">
        {providerInitials(provider)}
      </span>
      {source ? (
        // Provider marks are small local brand assets, not content images.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={source}
          alt=""
          aria-hidden="true"
          onError={(event) => {
            event.currentTarget.hidden = true;
            event.currentTarget.parentElement?.classList.add("fallback");
          }}
        />
      ) : null}
    </span>
  );
}

function harnessLabel(harness: string) {
  if (harness === "codex-cli") return "Codex CLI";
  if (harness === "claude-cli") return "Claude CLI";
  if (harness === "grok-cli") return "Grok CLI";
  if (harness === "opencode-cli") return "OpenCode CLI";
  return harness;
}

function reviewChoice(value: boolean | null | undefined, badWhenTrue = false) {
  if (typeof value !== "boolean") {
    return { valueLabel: "Not set", tone: "unset" };
  }

  const isBad = badWhenTrue ? value : !value;
  return {
    valueLabel: value ? "Yes" : "No",
    tone: isBad ? "negative" : "positive",
  };
}

function safeParseSgf(sgf: string | null | undefined, valid: boolean | undefined) {
  if (!sgf || !valid) return null;
  try {
    return parseSgf(sgf);
  } catch {
    return null;
  }
}

function defaultProblem(run: BenchmarkRun | undefined) {
  return run?.problems.find((problem) => problem.validation.valid && problem.sgf) ?? run?.problems[0];
}

function defaultRun() {
  return runs.find((run) => run.problems.some((problem) => problem.validation.valid && problem.sgf)) ?? runs[0];
}

const fallbackRun = defaultRun();

function humanCreditedProblemCount(run: BenchmarkRun) {
  return difficultyCappedHumanScore(run.problems).creditedProblems;
}

function humanReviewProgressForRun(
  record: BenchmarkRun,
  liveReviewProgress: ReviewProgressSnapshot | null,
) {
  const required = record.summary.humanReviewPending;
  const indexedCompleted = Math.max(
    0,
    ...(record.humanReviews?.reviewers.map((reviewer) => reviewer.completed) ?? []),
  );
  const liveCompleted = liveReviewProgress?.runId === record.runId
    ? Object.values(liveReviewProgress.problems).filter(
        (progress) => progress === "completed",
      ).length
    : 0;
  const completed = Math.max(indexedCompleted, liveCompleted);

  return {
    completed,
    remaining: Math.max(0, required - completed),
    required,
  };
}

function displayRunStatus(
  record: BenchmarkRun,
  reviewProgress: ReturnType<typeof humanReviewProgressForRun>,
) {
  return record.status === "needs_human_review" &&
    reviewProgress.required > 0 &&
    reviewProgress.remaining === 0
    ? "reviewed"
    : record.status;
}

export function runHasSgfFiles(record: {
  summary: { filesFound?: number };
  problems: Array<{ sgf: string | null }>;
}) {
  if (typeof record.summary.filesFound === "number") {
    return record.summary.filesFound > 0;
  }
  return record.problems.some(
    (problem) => typeof problem.sgf === "string" && problem.sgf.trim().length > 0,
  );
}

function rememberBrowserSelection(runId: string, problemFile: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("run", runId);
  url.searchParams.set("problem", problemFile);
  window.history.replaceState(
    window.history.state,
    "",
    `${url.pathname}${url.search}${url.hash}`,
  );
}

export function RunBrowser() {
  const [selectedRunId, setSelectedRunId] = useState(fallbackRun?.runId ?? "");
  const run = runs.find((record) => record.runId === selectedRunId) ?? fallbackRun;
  const [selectedProblemFile, setSelectedProblemFile] = useState(defaultProblem(run)?.file ?? "");
  const [liveReviewProgress, setLiveReviewProgress] = useState<ReviewProgressSnapshot | null>(null);
  const [sgfCopyState, setSgfCopyState] = useState<{
    file: string;
    status: "copied" | "failed";
  } | null>(null);
  const problem =
    run?.problems.find((record) => record.file === selectedProblemFile) ?? defaultProblem(run);
  const root = safeParseSgf(problem?.sgf, problem?.validation.valid);
  const [selectedNodeId, setSelectedNodeId] = useState("n0");
  const nodes = root ? walkSgf(root) : [];
  const selected = nodes.find((node) => node.id === selectedNodeId) ?? root;
  const stats = root ? getProblemStats(root) : null;
  const rightNodes = root ? collectRightNodes(root) : [];

  const chooseNode = (node: SgfNode) => setSelectedNodeId(node.id);
  const chooseRun = (runId: string) => {
    const nextRun = runs.find((record) => record.runId === runId);
    const nextProblemFile = defaultProblem(nextRun)?.file ?? "";
    setSelectedRunId(runId);
    setSelectedProblemFile(nextProblemFile);
    setSelectedNodeId("n0");
    if (nextProblemFile) rememberBrowserSelection(runId, nextProblemFile);
  };
  const chooseProblem = (file: string) => {
    setSelectedProblemFile(file);
    setSelectedNodeId("n0");
    rememberBrowserSelection(run.runId, file);
  };
  const updateReviewProgress = useCallback((snapshot: ReviewProgressSnapshot | null) => {
    setLiveReviewProgress(snapshot);
  }, []);
  const copyProblemSgf = async () => {
    if (!problem?.sgf) return;
    const file = problem.file;
    try {
      await navigator.clipboard.writeText(problem.sgf);
      setSgfCopyState({ file, status: "copied" });
    } catch {
      setSgfCopyState({ file, status: "failed" });
    }
    window.setTimeout(() => {
      setSgfCopyState((current) => (current?.file === file ? null : current));
    }, 1800);
  };
  const previousNode = selected?.parent;
  const nextNode = selected?.children[0];
  const path = selected ? getPath(selected) : [];
  const selectedMove = selected ? getMove(selected) : undefined;
  const selectedMoveNumber = path.filter(getMove).length;
  const comment = selected ? visibleComment(selected) : "";
  const boardSize = root ? getBoardSize(root) : 19;
  const firstMove = root?.children.map(getMove).find(Boolean);
  const playerColor =
    problem?.playerColor ??
    (firstMove?.color === "B" ? "black" : firstMove?.color === "W" ? "white" : null);
  const playerName = playerColor === "black" ? "Black" : playerColor === "white" ? "White" : null;
  const indexedReviews = problem?.reviews ?? [];
  const completedReviews = indexedReviews.filter(reviewProblemIsComplete);
  const ratedReviews = completedReviews.filter((review) => review.quality !== null);
  const startedReviewCount = indexedReviews.filter(
    (review) => reviewProblemProgress(review) === "started",
  ).length;
  const automaticallyRejectedFiles = run?.problems
    .filter((record) => record.automatedGate === "fail")
    .map((record) => record.file) ?? [];
  const duplicateReviewCount = completedReviews.filter((review) => review.duplicate).length;
  const averageQuality = ratedReviews.length
    ? ratedReviews.reduce((total, review) => total + (review.quality ?? 0), 0) / ratedReviews.length
    : null;
  const humanReviewSummary = completedReviews.length
    ? [
        `${completedReviews.length} review${completedReviews.length === 1 ? "" : "s"}`,
        averageQuality !== null ? `${averageQuality.toFixed(1)}★` : null,
        duplicateReviewCount
          ? `${duplicateReviewCount} duplicate flag${duplicateReviewCount === 1 ? "" : "s"}`
          : null,
        startedReviewCount ? `${startedReviewCount} in progress` : null,
      ].filter(Boolean).join(" · ")
    : startedReviewCount
      ? `${startedReviewCount} in progress`
      : problem?.human?.status ?? "pending";
  const originalityFlagged = run?.originalityTool
    ? run.originalityTool.results.duplicate + run.originalityTool.results.review
    : 0;
  const originalityErrors = run?.originalityTool
    ? run.originalityTool.results.invalid +
      run.originalityTool.results.unavailable +
      run.originalityTool.quotaExceeded
    : 0;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedRunId = params.get("run");
    const requestedRun = runs.find((record) => record.runId === requestedRunId);
    const targetRun = requestedRun ?? fallbackRun;
    const requestedProblemFile = params.get("problem");
    const requestedProblem = targetRun?.problems.find(
      (record) => record.file === requestedProblemFile,
    );
    if (!targetRun || (!requestedRun && !requestedProblem)) return;
    const selectionTimer = window.setTimeout(() => {
      setSelectedRunId(targetRun.runId);
      setSelectedProblemFile(requestedProblem?.file ?? defaultProblem(targetRun)?.file ?? "");
      setSelectedNodeId("n0");
    }, 0);
    return () => window.clearTimeout(selectionTimer);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) {
        return;
      }
      if (event.key === "ArrowLeft" && previousNode) chooseNode(previousNode);
      if (event.key === "ArrowRight" && nextNode) chooseNode(nextNode);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [nextNode, previousNode]);

  if (!runs.length) {
    return (
      <section className="runs-section" id="runs" aria-labelledby="runs-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Generated problems</p>
            <h2 id="runs-title">Benchmark runs</h2>
          </div>
          <p>Completed command-line runs appear here with their boards, trees, and evaluation results.</p>
        </div>
        <div className="run-empty">
          <span>No runs checked in yet</span>
          <code>python benchmark.py run --harness &lt;codex|claude|grok|opencode&gt; --model &lt;model-id&gt;</code>
        </div>
      </section>
    );
  }

  if (!run || !problem) return null;

  const selectedRunReviewProgress = humanReviewProgressForRun(run, liveReviewProgress);
  const selectedRunDisplayStatus = displayRunStatus(run, selectedRunReviewProgress);
  const runHumanScore = difficultyCappedHumanScore(run.problems);
  const runHumanScoreTitle = [
    `${runHumanScore.counts.twentyToThirtyKyu} passing at 20-30 kyu (maximum 2 credited)`,
    `${runHumanScore.counts.tenToNineteenKyu} passing at 10-19 kyu (maximum 2 credited)`,
    `${runHumanScore.counts.fiveKyuOrHarder} passing at 5-9 kyu or harder (uncapped)`,
    runHumanScore.counts.unrated
      ? `${runHumanScore.counts.unrated} passing without a difficulty rating (not credited)`
      : null,
  ].filter(Boolean).join("; ");

  const structuralCheck: RunCheck = {
    id: "structural",
    status: problem.validation.valid ? "pass" : "fail",
    message: problem.validation.valid
      ? "The SGF passed the automated structural and legality checks."
      : "The SGF failed one or more automated structural checks.",
  };
  const peerDuplicate = problem.originality.peerExactMatches.length > 0;
  const peerReview = problem.originality.peerShapeMatches.length > 0;
  const effectiveOriginalityStatus =
    peerDuplicate || problem.originality.status === "fail"
      ? "fail"
      : peerReview || problem.originality.status === "manual_review"
        ? "needs_human_review"
        : problem.originality.status === "pass"
          ? "pass"
          : "not_run";
  const originalityCheck: RunCheck = {
    id: "originality",
    status: effectiveOriginalityStatus,
    message:
      problem.originality.builtInSetupMatch
        ? `Built-in common setup match: ${problem.originality.builtInSetupMatch.label}.`
        : peerDuplicate
        ? `Exact transformed match within this run: ${problem.originality.peerExactMatches.join(", ")}.`
        : peerReview
          ? `Another generated problem has a similar solution shape: ${problem.originality.peerShapeMatches.map((match) => `${match.file} (${Math.round(match.percentage)}%)`).join(", ")}.`
          : problem.originality.status === "pass"
            ? "Local and remote duplicate gates passed."
            : problem.originality.status === "fail"
              ? "A duplicate gate failed."
              : problem.originality.status === "manual_review"
                ? "Similarity requires side-by-side human review."
                : "The full remote duplicate result is not available.",
  };
  const checks = [structuralCheck, originalityCheck, ...(run.runChecks ?? [])];

  return (
    <section className="runs-section" id="runs" aria-labelledby="runs-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Generated problems</p>
          <h2 id="runs-title">Benchmark runs</h2>
        </div>
        <p>Select a run and problem to inspect the generated position, solution tree, and recorded checks.</p>
      </div>

      <div className="workbench-shell run-workbench-shell">
        <aside className="problem-library run-library" aria-label="Benchmark run library">
          <div className="library-header">
            <div><span className="library-count">{runs.length}</span><span>runs</span></div>
            <span>CLI RUNS</span>
          </div>
          <div className="problem-list">
            {runs.map((record) => {
              const humanPassed = humanCreditedProblemCount(record);
              const automatedPassed = record.summary.automatedGatePassed;
              const totalProblems = record.summary.expectedProblems ?? record.problems.length;
              const showPassCounts = runHasSgfFiles(record);
              const recordReviewProgress = humanReviewProgressForRun(record, liveReviewProgress);
              const recordDisplayStatus = displayRunStatus(record, recordReviewProgress);

              return (
                <button
                  type="button"
                  key={record.runId}
                  className={`problem-list-item${record.runId === run.runId ? " active" : ""}`}
                  onClick={() => chooseRun(record.runId)}
                  aria-pressed={record.runId === run.runId}
                >
                  <span className="run-provider-cell">
                    <ProviderMark provider={record.model.provider} />
                    <span
                      className={`run-status-dot ${recordDisplayStatus}`}
                      role="img"
                      aria-label={`Run status: ${statusLabel(recordDisplayStatus)}`}
                      title={`Run status: ${statusLabel(recordDisplayStatus)}`}
                    />
                  </span>
                  <span className="problem-list-copy">
                    <span className="problem-list-topline">
                      <strong
                        aria-label={record.model.name}
                        title={record.model.name}
                      >
                        {compactModelName(record.model.name)}
                      </strong>
                      {showPassCounts ? (
                        <span
                          className="run-pass-counts"
                          aria-label={`${humanPassed} difficulty-credited, ${automatedPassed} automated passed, ${totalProblems} total problems`}
                          title="Difficulty-credited / automated passed / total problems"
                        >
                          {humanPassed}/{automatedPassed}/{totalProblems}
                        </span>
                      ) : null}
                    </span>
                    <span className="run-effort">{effortLabel(record.model.reasoningEffort)}</span>
                    <small>{humanDate(record.createdAt)}</small>
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="problem-stage run-stage">
          <header className="problem-stage-header">
            <div>
              <div className="record-kicker">
                <span>{providerLabel(run.model.provider)} / {harnessLabel(run.harness.name)}</span>
                <span className={`run-badge ${selectedRunDisplayStatus}`}>
                  {statusLabel(selectedRunDisplayStatus)}
                </span>
              </div>
              <h3 aria-label={run.model.name} title={run.model.name}>
                {compactModelName(run.model.name)}
              </h3>
              <p>
                {humanDate(run.createdAt)} · {run.model.reasoningEffort ?? "default effort"} · {formatDurationSeconds(run.harness.durationSeconds)}
              </p>
            </div>
            <div className="run-summary" aria-label="Run summary">
              <span><strong>{run.summary.structuralPassed}</strong> structural</span>
              <span><strong>{run.summary.originalityPassed}</strong> original</span>
              <span><strong>{selectedRunReviewProgress.remaining}</strong> to review</span>
              <span
                title={runHumanScoreTitle}
              >
                <strong>{runHumanScore.creditedProblems}</strong> human score
              </span>
              {run.originalityTool ? (
                <>
                  <span
                    title={`${run.originalityTool.queriesRemaining} queries remaining`}
                    aria-label={`${run.originalityTool.queriesUsed} of ${run.originalityTool.queryLimit} originality queries used`}
                  >
                    <strong>{run.originalityTool.queriesUsed} / {run.originalityTool.queryLimit}</strong>
                    queries used
                  </span>
                  <span
                    className="originality-result-summary"
                    title={`${run.originalityTool.results.clear} clear, ${originalityFlagged} flagged, ${originalityErrors} errors`}
                  >
                    <strong>{run.originalityTool.results.clear} / {originalityFlagged} / {originalityErrors}</strong>
                    clear / flagged / error
                  </span>
                </>
              ) : null}
            </div>
          </header>

          <div className="run-problem-tabs" aria-label="Generated problems">
            {run.problems.map((record) => {
              const reviewProgress: ReviewProblemProgress =
                liveReviewProgress?.runId === run.runId
                  ? liveReviewProgress.problems[record.file] ?? "untouched"
                  : aggregateReviewProgress(record.reviews ?? []);
              const progressClass = reviewProgress === "untouched" ? "" : ` review-${reviewProgress}`;
              const humanMarkedBad =
                liveReviewProgress?.runId === run.runId
                  ? liveReviewProgress.badProblems.includes(record.file)
                  : record.reviews?.some(isReviewMarkedBad) ?? false;
              const humanBadClass = humanMarkedBad ? " human-rejected" : "";
              const reviewLabel =
                reviewProgress === "completed"
                  ? "human review completed"
                  : reviewProgress === "started"
                    ? "human review started"
                    : "not yet reviewed";
              return (
                <button
                  type="button"
                  key={record.file}
                  className={record.file === problem.file ? "active" : ""}
                  onClick={() => chooseProblem(record.file)}
                  aria-pressed={record.file === problem.file}
                >
                  <ProblemThumbnail sgf={record.sgf} />
                  <span className="run-problem-tab-copy">
                    <span>{record.file.replace(".sgf", "")}</span>
                    <small>{record.targetDifficulty}</small>
                  </span>
                  <i
                    className={`${record.status}${progressClass}${humanBadClass}`}
                    role="img"
                    aria-label={`${statusLabel(record.status)}; ${reviewLabel}${humanMarkedBad ? "; human review found a problem" : ""}`}
                  />
                </button>
              );
            })}
          </div>

          <HumanReviewPanel
            runId={run.runId}
            problemFile={problem.file}
            automaticallyRejectedFiles={automaticallyRejectedFiles}
            onChooseProblem={chooseProblem}
            onReviewProgressChange={updateReviewProgress}
          />

          {root && selected && stats ? (
            <div className="stage-grid run-stage-grid">
              <div className="board-column">
                <div className="move-inspector" aria-live="polite">
                  <div className="move-inspector-main">
                    <span className="move-label">
                      {selectedMove
                        ? `MOVE ${selectedMoveNumber} · ${selectedMove.color === "B" ? "BLACK" : "WHITE"}`
                        : "ROOT · SETUP"}
                    </span>
                    <strong>
                      {selectedMove ? pointToHuman(selectedMove.point, boardSize) : "Starting position"}
                    </strong>
                    <p>
                      {comment ||
                        (hasControlTag(selected, "RIGHT")
                          ? "Accepted solution endpoint."
                          : selectedMove
                            ? "Continue through the selected variation."
                            : `${problem.targetDifficulty} target.`)}
                    </p>
                  </div>
                </div>
                <div className="board-frame">
                  <div className="board-toolbar">
                    <span className="board-toolbar-label">GENERATED POSITION</span>
                    <div className="board-primary-controls">
                      {playerColor && playerName && (
                        <span
                          className={`to-move-stone ${playerColor}`}
                          role="img"
                          aria-label={`${playerName} to play`}
                          title={`${playerName} to play`}
                        />
                      )}
                      <div className="board-controls" aria-label="Generated board navigation controls">
                        <button type="button" onClick={() => chooseNode(root)} disabled={selected === root} aria-label="Reset to setup">↺</button>
                        <button type="button" onClick={() => previousNode && chooseNode(previousNode)} disabled={!previousNode} aria-label="Previous move">←</button>
                        <button type="button" onClick={() => nextNode && chooseNode(nextNode)} disabled={!nextNode} aria-label="Next default move">→</button>
                        <button type="button" className="reveal-button" onClick={() => rightNodes[0] && chooseNode(rightNodes[0])}>Reveal</button>
                      </div>
                    </div>
                    <div className="board-variation-legend" id="run-board-variation-legend">
                      <span><i className="board-marker-right" aria-hidden="true" /> RIGHT</span>
                      <span><i className="board-marker-wrong" aria-hidden="true" /> NO RIGHT</span>
                    </div>
                  </div>
                  <GoBoard
                    root={root}
                    selected={selected}
                    onSelect={chooseNode}
                    variationLegendId="run-board-variation-legend"
                  />
                </div>
              </div>
              <div className="tree-column">
                <div className="tree-panel-header">
                  <div>
                    <span className="panel-label">SOLUTION TREE</span>
                    <strong>{stats.nodeCount} nodes across {stats.variationPoints} forks</strong>
                  </div>
                  <div className="tree-legend">
                    <span><i className="legend-right" /> Leads to RIGHT</span>
                    <span><i className="legend-wrong" /> No RIGHT</span>
                  </div>
                </div>
                <div className="tree-summary">
                  <div><span>SETUP</span><strong>{stats.setupStoneCount}</strong><small>stones</small></div>
                  <div><span>DEPTH</span><strong>{stats.maxDepth}</strong><small>moves max</small></div>
                  <div><span>RIGHT</span><strong>{stats.rightCount}</strong><small>accepted lines</small></div>
                  <div><span>TARGET</span><strong className="target-rank">{problem.targetDifficulty}</strong></div>
                </div>
                <SolutionTree root={root} selected={selected} onSelect={chooseNode} />
              </div>
            </div>
          ) : (
            <div className="invalid-output">
              <span>SGF unavailable</span>
              <h4>{problem.file} cannot be rendered.</h4>
              <p>The failed checks below preserve the model’s output as part of the run.</p>
              {problem.sgf && <pre>{problem.sgf}</pre>}
            </div>
          )}

          <div className="run-evaluation-grid">
            <div>
              <span className="panel-label">AUTOMATED CHECKS</span>
              <ul className="check-list">
                {checks.map((check) => (
                  <li key={check.id} className={check.status}>
                    <i aria-hidden="true" />
                    <div><strong>{statusLabel(check.status)}</strong><p>{check.message}</p></div>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <span className="panel-label">DETAILS</span>
              <dl className="evaluation-details">
                <div><dt>Target difficulty</dt><dd>{problem.targetDifficulty}</dd></div>
                <div>
                  <dt>Human review</dt>
                  <dd>{humanReviewSummary}</dd>
                </div>
                {problem.originality.builtInSetupMatch && (
                  <div>
                    <dt>Built-in common setup</dt>
                    <dd>{problem.originality.builtInSetupMatch.label}</dd>
                  </div>
                )}
                <div><dt>Closest reference</dt><dd>{problem.originality.closestLocalShape ? `#${problem.originality.closestLocalShape.id} · ${Math.round(problem.originality.closestLocalShape.percentage)}%` : "not available"}</dd></div>
                <div>
                  <dt>Remote top match</dt>
                  <dd>
                    {problem.originality.remote.topPercentage === null
                      ? "not available"
                      : (
                          <>
                            {problem.originality.remote.topPercentage}%
                            {problem.originality.remote.topMatchId && (
                              <>
                                {" · "}
                                <a
                                  href={`https://www.goproblems.com/problems/${problem.originality.remote.topMatchId}`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  #{problem.originality.remote.topMatchId} ↗
                                </a>
                              </>
                            )}
                          </>
                        )}
                  </dd>
                </div>
              </dl>
              {indexedReviews.length > 0 && (
                <section className="recorded-reviews" aria-labelledby="recorded-reviews-title">
                  <span className="recorded-reviews-title" id="recorded-reviews-title">
                    Human review choices
                  </span>
                  <div className="recorded-review-list">
                    {indexedReviews.map((review) => {
                      const choices = [
                        { name: "Valid", ...reviewChoice(review.valid) },
                        { name: "Realistic", ...reviewChoice(review.realistic) },
                        { name: "Duplicate", ...reviewChoice(review.duplicate, true) },
                        { name: "Well pathed", ...reviewChoice(review.wellPathed) },
                      ];

                      return (
                        <article className="recorded-review" key={review.reviewId}>
                          <header>
                            <strong>{review.reviewerName}</strong>
                            <span className={review.status}>
                              {review.status === "completed" ? "Reviewed" : "In progress"}
                            </span>
                          </header>
                          <dl>
                            {choices.map((choice) => (
                              <div key={choice.name}>
                                <dt>{choice.name}</dt>
                                <dd className={choice.tone}>{choice.valueLabel}</dd>
                              </div>
                            ))}
                            <div>
                              <dt>Difficulty</dt>
                              <dd className={review.estimatedDifficulty ? undefined : "unset"}>
                                {review.estimatedDifficulty ?? "Not set"}
                              </dd>
                            </div>
                            <div>
                              <dt>Quality</dt>
                              <dd className={review.quality === null ? "unset" : undefined}>
                                {review.quality === null ? "Not rated" : `${review.quality} / 5`}
                              </dd>
                            </div>
                          </dl>
                        </article>
                      );
                    })}
                  </div>
                </section>
              )}
              {problem.validation.issues.length > 0 && (
                <ul className="issue-list">
                  {problem.validation.issues.map((issue, index) => (
                    <li key={`${issue.code}-${index}`} className={issue.severity}>
                      <strong>{issue.code}</strong> {issue.message}
                    </li>
                  ))}
                </ul>
              )}
              <section className="sgf-source" aria-label={`SGF source for ${problem.file}`}>
                <div className="sgf-source-bar">
                  <div>
                    <span>SGF SOURCE</span>
                    <code>{problem.file}</code>
                  </div>
                  <button
                    type="button"
                    onClick={copyProblemSgf}
                    disabled={!problem.sgf}
                    className={
                      sgfCopyState?.file === problem.file ? sgfCopyState.status : undefined
                    }
                    aria-live="polite"
                  >
                    {sgfCopyState?.file === problem.file
                      ? sgfCopyState.status === "copied"
                        ? "Copied"
                        : "Copy failed"
                      : "Copy SGF"}
                  </button>
                </div>
                {problem.sgf ? (
                  <details>
                    <summary>Reveal SGF source</summary>
                    <pre>{problem.sgf}</pre>
                  </details>
                ) : (
                  <p className="sgf-source-empty">No SGF source was produced for this problem.</p>
                )}
              </section>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
