"use client";

import { useEffect, useMemo, useState } from "react";
import problemData from "../data/problems.generated.json";
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

interface ProblemRecord {
  id: number;
  label: string;
  rank: string;
  rankValue: number;
  rankUnit: string;
  elo: number;
  playerColor: "black" | "white";
  genre: string;
  author: string;
  source: string;
  createdAt: string;
  rating: { stars: number; votes: number };
  attempts: { solved: number; failed: number; tries: number };
  avgSolveTimeSeconds: number;
  canonical: boolean;
  standard: boolean;
  sourceUrl: string;
  sgfFile: string;
  sgf: string;
}

const problems = problemData as ProblemRecord[];

export function ProblemWorkbench() {
  const [selectedProblemId, setSelectedProblemId] = useState(problems[0].id);
  const [selectedNodeId, setSelectedNodeId] = useState("n0");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [copied, setCopied] = useState(false);

  const problem = problems.find((record) => record.id === selectedProblemId) ?? problems[0];
  const root = useMemo(() => parseSgf(problem.sgf), [problem.sgf]);
  const nodes = useMemo(() => walkSgf(root), [root]);
  const selected = nodes.find((node) => node.id === selectedNodeId) ?? root;
  const stats = useMemo(() => getProblemStats(root), [root]);
  const boardSize = getBoardSize(root);
  const rightNodes = useMemo(() => collectRightNodes(root), [root]);
  const playerName = problem.playerColor === "black" ? "Black" : "White";

  const filteredProblems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return problems.filter((record) => {
      const matchesQuery =
        !needle ||
        [record.id, record.rank, record.playerColor, record.author, record.source]
          .join(" ")
          .toLowerCase()
          .includes(needle);
      const matchesFilter =
        filter === "all" ||
        (filter === "20-30k" && record.rankUnit === "kyu" && record.rankValue >= 20) ||
        (filter === "10-19k" &&
          record.rankUnit === "kyu" &&
          record.rankValue >= 10 &&
          record.rankValue <= 19) ||
        (filter === "5-9k" &&
          record.rankUnit === "kyu" &&
          record.rankValue >= 5 &&
          record.rankValue <= 9) ||
        (filter === "1-4k" &&
          record.rankUnit === "kyu" &&
          record.rankValue >= 1 &&
          record.rankValue <= 4) ||
        (filter === "1d" && record.rankUnit === "dan" && record.rankValue === 1) ||
        filter === record.playerColor;
      return matchesQuery && matchesFilter;
    });
  }, [filter, query]);

  const path = getPath(selected);
  const selectedMove = getMove(selected);
  const selectedMoveNumber = path.filter(getMove).length;
  const comment = visibleComment(selected);

  const chooseProblem = (id: number) => {
    setSelectedProblemId(id);
    setSelectedNodeId("n0");
    setCopied(false);
  };

  const chooseNode = (node: SgfNode) => setSelectedNodeId(node.id);
  const previousNode = selected.parent;
  const nextNode = selected.children[0];

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

  const copySgf = async () => {
    await navigator.clipboard.writeText(problem.sgf);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const downloadSgf = () => {
    const url = URL.createObjectURL(new Blob([`${problem.sgf}\n`], { type: "application/x-go-sgf" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `gp-${problem.id}.sgf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="workbench-section" id="workbench" aria-labelledby="workbench-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Reference problems</p>
          <h2 id="workbench-title">Problem viewer</h2>
        </div>
        <p>
          Select a problem, then select any node in its solution tree to replay the position on
          the board.
        </p>
      </div>

      <div className="workbench-shell">
        <aside className="problem-library" aria-label="Reference problem library">
          <div className="library-header">
            <div>
              <span className="library-count">{problems.length}</span>
              <span>reference problems</span>
            </div>
            <span className="live-dot">30K–1D · API CHECKED</span>
          </div>
          <label className="search-field">
            <span className="sr-only">Search reference problems</span>
            <span aria-hidden="true">⌕</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search ID, rank, source…"
            />
          </label>
          <div className="filter-row" aria-label="Filter problems">
            {[
              ["all", "All"],
              ["20-30k", "20–30k"],
              ["10-19k", "10–19k"],
              ["5-9k", "5–9k"],
              ["1-4k", "1–4k"],
              ["1d", "1d"],
              ["black", "Black"],
              ["white", "White"],
            ].map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={filter === value ? "active" : ""}
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="problem-list">
            {filteredProblems.map((record) => (
              <button
                type="button"
                key={record.id}
                className={`problem-list-item${record.id === problem.id ? " active" : ""}`}
                onClick={() => chooseProblem(record.id)}
                aria-pressed={record.id === problem.id}
                aria-label={`Problem ${record.id}, ${
                  record.playerColor === "black" ? "Black" : "White"
                } to play, ${record.rank}, by ${record.author}`}
              >
                <span className={`mini-stone ${record.playerColor}`} aria-hidden="true" />
                <span className="problem-list-copy">
                  <span className="problem-list-topline">
                    <strong>#{record.id}</strong>
                    <span>{record.rank}</span>
                  </span>
                  <small>
                    {record.author} · {record.attempts.tries.toLocaleString()} tries
                  </small>
                </span>
              </button>
            ))}
            {!filteredProblems.length && (
              <div className="empty-list">No references match that filter.</div>
            )}
          </div>
        </aside>

        <div className="problem-stage">
          <header className="problem-stage-header">
            <div>
              <div className="record-kicker">
                <span>GO PROBLEMS / {problem.id}</span>
                <span className="standard-badge">CANON · STANDARD</span>
              </div>
              <h3>{playerName} to play</h3>
              <p>
                <span className={`inline-stone ${problem.playerColor}`} aria-hidden="true" />
                {problem.rank}
                {problem.source !== "Not listed" ? ` · ${problem.source}` : ""}
              </p>
            </div>
            <div className="problem-actions">
              <button type="button" onClick={copySgf}>{copied ? "Copied" : "Copy SGF"}</button>
              <button type="button" onClick={downloadSgf}>Download</button>
              <a href={problem.sourceUrl} target="_blank" rel="noreferrer">Original ↗</a>
            </div>
          </header>

          <div className="stage-grid">
            <div className="board-column">
              <div className="board-frame">
                <div className="board-toolbar">
                  <span className="board-toolbar-label">POSITION</span>
                  <div className="board-controls" aria-label="Board navigation controls">
                    <button
                      type="button"
                      onClick={() => chooseNode(root)}
                      disabled={selected === root}
                      aria-label="Reset to setup"
                      title="Reset to setup"
                    >
                      ↺
                    </button>
                    <button
                      type="button"
                      onClick={() => previousNode && chooseNode(previousNode)}
                      disabled={!previousNode}
                      aria-label="Previous move"
                      title="Previous move"
                    >
                      ←
                    </button>
                    <button
                      type="button"
                      onClick={() => nextNode && chooseNode(nextNode)}
                      disabled={!nextNode}
                      aria-label="Next default move"
                      title="Next move"
                    >
                      →
                    </button>
                    <button
                      type="button"
                      className="reveal-button"
                      onClick={() => rightNodes[0] && chooseNode(rightNodes[0])}
                      aria-label="Reveal accepted line"
                    >
                      Reveal
                    </button>
                  </div>
                  <div
                    className="board-variation-legend"
                    id="board-variation-legend"
                    aria-label="Board variation legend"
                  >
                    <span><i className="board-marker-right" aria-hidden="true" /> RIGHT</span>
                    <span><i className="board-marker-wrong" aria-hidden="true" /> NO RIGHT</span>
                  </div>
                </div>
                <GoBoard root={root} selected={selected} onSelect={chooseNode} />
              </div>

              <div className="move-inspector" aria-live="polite">
                <div className="move-inspector-main">
                  <span className="move-label">
                    {selectedMove
                      ? `MOVE ${selectedMoveNumber} · ${selectedMove.color === "B" ? "BLACK" : "WHITE"}`
                      : "ROOT · SETUP"}
                  </span>
                  <strong>
                    {selectedMove
                      ? pointToHuman(selectedMove.point, boardSize)
                      : "Starting position"}
                  </strong>
                  <p>
                    {comment ||
                      (hasControlTag(selected, "RIGHT")
                        ? "Accepted solution endpoint."
                        : hasControlTag(selected, "CHOICE")
                          ? "A marked defensive choice."
                          : selectedMove
                            ? "Continue through the selected variation."
                            : `${playerName} to play.`)}
                  </p>
                </div>
              </div>
            </div>

            <div className="tree-column">
              <div className="tree-panel-header">
                <div>
                  <span className="panel-label">SOLUTION TREE</span>
                  <strong>{stats.nodeCount} nodes across {stats.variationPoints} forks</strong>
                </div>
                <div className="tree-legend" aria-label="Solution tree legend">
                  <span><i className="legend-right" /> Leads to RIGHT</span>
                  <span><i className="legend-wrong" /> No RIGHT</span>
                </div>
              </div>
              <SolutionTree root={root} selected={selected} onSelect={chooseNode} />
              <div className="tree-summary">
                <div><span>SETUP</span><strong>{stats.setupStoneCount}</strong><small>stones</small></div>
                <div><span>DEPTH</span><strong>{stats.maxDepth}</strong><small>moves max</small></div>
                <div><span>RIGHT</span><strong>{stats.rightCount}</strong><small>accepted lines</small></div>
                <div><span>AVG</span><strong>{problem.avgSolveTimeSeconds}s</strong><small>solve time</small></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
