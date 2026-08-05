"use client";

import { useEffect, useState } from "react";
import runData from "../data/runs.generated.json";
import { GoBoard } from "./GoBoard";
import { SolutionTree } from "./SolutionTree";
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
  summary: {
    expectedProblems?: number;
    structuralPassed: number;
    originalityPassed: number;
    automatedGatePassed: number;
    failedProblems: number;
    incompleteProblems: number;
    humanReviewPending: number;
    failedRunChecks: number;
  };
  runChecks?: RunCheck[];
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

export function RunBrowser() {
  const [selectedRunId, setSelectedRunId] = useState(runs[0]?.runId ?? "");
  const run = runs.find((record) => record.runId === selectedRunId) ?? runs[0];
  const [selectedProblemFile, setSelectedProblemFile] = useState(defaultProblem(run)?.file ?? "");
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
    setSelectedRunId(runId);
    setSelectedProblemFile(defaultProblem(nextRun)?.file ?? "");
    setSelectedNodeId("n0");
  };
  const chooseProblem = (file: string) => {
    setSelectedProblemFile(file);
    setSelectedNodeId("n0");
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
          <code>python benchmark.py run --model &lt;openai-model-id&gt;</code>
        </div>
      </section>
    );
  }

  if (!run || !problem) return null;

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
      peerDuplicate
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
            <span>CODEX CLI</span>
          </div>
          <div className="problem-list">
            {runs.map((record) => (
              <button
                type="button"
                key={record.runId}
                className={`problem-list-item${record.runId === run.runId ? " active" : ""}`}
                onClick={() => chooseRun(record.runId)}
                aria-pressed={record.runId === run.runId}
              >
                <span className={`run-status-dot ${record.status}`} aria-hidden="true" />
                <span className="problem-list-copy">
                  <span className="problem-list-topline">
                    <strong>{record.model.name}</strong>
                    <span>
                      {record.summary.automatedGatePassed}/
                      {record.summary.expectedProblems ?? record.problems.length}
                    </span>
                  </span>
                  <small>{humanDate(record.createdAt)}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <div className="problem-stage run-stage">
          <header className="problem-stage-header">
            <div>
              <div className="record-kicker">
                <span>OPENAI / CODEX CLI</span>
                <span className={`run-badge ${run.status}`}>{statusLabel(run.status)}</span>
              </div>
              <h3>{run.model.name}</h3>
              <p>
                {humanDate(run.createdAt)} · {run.model.reasoningEffort ?? "default effort"} · {run.harness.durationSeconds ?? 0}s
              </p>
            </div>
            <div className="run-summary" aria-label="Run summary">
              <span><strong>{run.summary.structuralPassed}</strong> structural</span>
              <span><strong>{run.summary.originalityPassed}</strong> original</span>
              <span><strong>{run.summary.humanReviewPending}</strong> to review</span>
            </div>
          </header>

          <div className="run-problem-tabs" aria-label="Generated problems">
            {run.problems.map((record) => (
              <button
                type="button"
                key={record.file}
                className={record.file === problem.file ? "active" : ""}
                onClick={() => chooseProblem(record.file)}
                aria-pressed={record.file === problem.file}
              >
                <span>{record.file.replace(".sgf", "")}</span>
                <small>{record.targetDifficulty}</small>
                <i className={record.status} aria-label={statusLabel(record.status)} />
              </button>
            ))}
          </div>

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
                <div><dt>Human review</dt><dd>{problem.human?.status ?? "pending"}</dd></div>
                <div><dt>Closest reference</dt><dd>{problem.originality.closestLocalShape ? `#${problem.originality.closestLocalShape.id} · ${Math.round(problem.originality.closestLocalShape.percentage)}%` : "not available"}</dd></div>
                <div><dt>Remote top match</dt><dd>{problem.originality.remote.topPercentage === null ? "not available" : `${problem.originality.remote.topPercentage}%${problem.originality.remote.topMatchId ? ` · #${problem.originality.remote.topMatchId}` : ""}`}</dd></div>
              </dl>
              {problem.validation.issues.length > 0 && (
                <ul className="issue-list">
                  {problem.validation.issues.map((issue, index) => (
                    <li key={`${issue.code}-${index}`} className={issue.severity}>
                      <strong>{issue.code}</strong> {issue.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
