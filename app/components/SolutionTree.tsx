"use client";

import { useMemo } from "react";
import {
  getBoardSize,
  getMove,
  getPath,
  hasControlTag,
  pointToHuman,
  visibleComment,
  type SgfNode,
} from "@/lib/sgf";

interface SolutionTreeProps {
  root: SgfNode;
  selected: SgfNode;
  onSelect: (node: SgfNode) => void;
}

interface PositionedNode {
  node: SgfNode;
  x: number;
  y: number;
  moveNumber: number;
}

interface PositionedEdge {
  from: PositionedNode;
  to: PositionedNode;
  leadsToRight: boolean;
}

const NODE_SIZE = 26;
const COLUMN_STEP = 44;
const ROW_STEP = 34;
const TREE_PADDING = 18;

function createTreeLayout(root: SgfNode) {
  const positions = new Map<string, PositionedNode>();
  const resultByNode = new Map<string, boolean>();
  let nextLeaf = 0;
  let maxDepth = 0;

  const markResults = (node: SgfNode): boolean => {
    const childResults = node.children.map((child) => markResults(child));
    const hasResult = hasControlTag(node, "RIGHT") || childResults.some(Boolean);
    resultByNode.set(node.id, hasResult);
    return hasResult;
  };

  const placeNode = (node: SgfNode, depth: number, priorMoveNumber: number): number => {
    const moveNumber = priorMoveNumber + (getMove(node) ? 1 : 0);
    maxDepth = Math.max(maxDepth, depth);
    const childRows = node.children.map((child) => placeNode(child, depth + 1, moveNumber));
    const row = childRows.length
      ? (childRows[0] + childRows[childRows.length - 1]) / 2
      : nextLeaf++;

    positions.set(node.id, {
      node,
      x: TREE_PADDING + NODE_SIZE / 2 + depth * COLUMN_STEP,
      y: TREE_PADDING + NODE_SIZE / 2 + row * ROW_STEP,
      moveNumber,
    });
    return row;
  };

  markResults(root);
  placeNode(root, 0, 0);

  const nodes = Array.from(positions.values());
  const edges: PositionedEdge[] = [];
  for (const from of nodes) {
    for (const child of from.node.children) {
      const to = positions.get(child.id);
      if (to) {
        edges.push({
          from,
          to,
          leadsToRight: resultByNode.get(child.id) ?? false,
        });
      }
    }
  }

  return {
    nodes,
    edges,
    width: TREE_PADDING * 2 + NODE_SIZE + maxDepth * COLUMN_STEP,
    height: TREE_PADDING * 2 + NODE_SIZE + Math.max(0, nextLeaf - 1) * ROW_STEP,
  };
}

export function SolutionTree({ root, selected, onSelect }: SolutionTreeProps) {
  const selectedPath = useMemo(
    () => new Set(getPath(selected).map((node) => node.id)),
    [selected],
  );
  const layout = useMemo(() => createTreeLayout(root), [root]);
  const boardSize = getBoardSize(root);

  return (
    <div className="solution-tree-scroll" tabIndex={0} aria-label="Scrollable solution tree">
      <div
        className="compact-solution-tree"
        style={{ width: layout.width, height: layout.height }}
      >
        {layout.edges.map((edge) => {
          const deltaX = edge.to.x - edge.from.x;
          const deltaY = edge.to.y - edge.from.y;
          const length = Math.hypot(deltaX, deltaY);
          const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
          const onSelectedPath =
            selectedPath.has(edge.from.node.id) && selectedPath.has(edge.to.node.id);

          return (
            <span
              key={`${edge.from.node.id}-${edge.to.node.id}`}
              className={`tree-edge ${edge.leadsToRight ? "has-result" : "no-result"}${
                onSelectedPath ? " on-path" : ""
              }`}
              style={{
                left: edge.from.x,
                top: edge.from.y,
                width: length,
                transform: `rotate(${angle}deg)`,
              }}
              aria-hidden="true"
            />
          );
        })}

        {layout.nodes.map(({ node, x, y, moveNumber }) => {
          const move = getMove(node);
          const isRight = hasControlTag(node, "RIGHT");
          const isChoice = hasControlTag(node, "CHOICE");
          const comment = visibleComment(node);
          const label = move
            ? `${move.color === "B" ? "Black" : "White"} ${pointToHuman(
                move.point,
                boardSize,
              )}, move ${moveNumber}${isRight ? ", correct result" : ""}${
                isChoice ? ", choice" : ""
              }${comment ? `, ${comment}` : ""}`
            : "Starting position";

          return (
            <button
              type="button"
              key={node.id}
              className={`tree-node ${
                move ? `tree-stone ${move.color === "B" ? "black" : "white"}` : "tree-root"
              }${selected.id === node.id ? " selected" : ""}${isRight ? " is-right" : ""}${
                isChoice ? " is-choice" : ""
              }`}
              style={{ left: x - NODE_SIZE / 2, top: y - NODE_SIZE / 2 }}
              onClick={() => onSelect(node)}
              aria-label={label}
              title={label}
            >
              {!move && <span aria-hidden="true">⌂</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
