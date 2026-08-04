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

function TreeNode({
  node,
  root,
  selectedId,
  selectedPath,
  moveNumber,
  onSelect,
}: {
  node: SgfNode;
  root: SgfNode;
  selectedId: string;
  selectedPath: Set<string>;
  moveNumber: number;
  onSelect: (node: SgfNode) => void;
}) {
  const move = getMove(node);
  const isRight = hasControlTag(node, "RIGHT");
  const isChoice = hasControlTag(node, "CHOICE");
  const comment = visibleComment(node);
  const nextMoveNumber = moveNumber + (move ? 1 : 0);
  const label = move
    ? `${move.color === "B" ? "Black" : "White"} ${pointToHuman(
        move.point,
        getBoardSize(root),
      )}, move ${nextMoveNumber}${isRight ? ", correct" : ""}${
        isChoice ? ", choice" : ""
      }${comment ? `, ${comment}` : ""}`
    : "Setup position";

  return (
    <li>
      <div className="tree-node-wrap">
        <button
          type="button"
          className={`tree-node ${move ? `tree-stone ${move.color === "B" ? "black" : "white"}` : "tree-root"}${
            selectedPath.has(node.id) ? " on-path" : ""
          }${selectedId === node.id ? " selected" : ""}${isRight ? " is-right" : ""}${
            isChoice ? " is-choice" : ""
          }`}
          onClick={() => onSelect(node)}
          aria-label={label}
          title={label}
        >
          {move ? nextMoveNumber : "SET"}
        </button>
        {move && (
          <span className="tree-coordinate">
            {pointToHuman(move.point, getBoardSize(root))}
          </span>
        )}
        {(isRight || isChoice) && (
          <span className={`tree-status ${isRight ? "right" : "choice"}`}>
            {isRight ? "RIGHT" : "CHOICE"}
          </span>
        )}
      </div>
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              root={root}
              selectedId={selectedId}
              selectedPath={selectedPath}
              moveNumber={nextMoveNumber}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function SolutionTree({ root, selected, onSelect }: SolutionTreeProps) {
  const selectedPath = useMemo(
    () => new Set(getPath(selected).map((node) => node.id)),
    [selected],
  );

  return (
    <div className="solution-tree-scroll" tabIndex={0} aria-label="Scrollable solution tree">
      <ul className="solution-tree">
        <TreeNode
          node={root}
          root={root}
          selectedId={selected.id}
          selectedPath={selectedPath}
          moveNumber={0}
          onSelect={onSelect}
        />
      </ul>
    </div>
  );
}

