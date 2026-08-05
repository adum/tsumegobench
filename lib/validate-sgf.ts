import {
  collectRightNodes,
  expandPointValues,
  getBoardSize,
  getMove,
  getNodeComment,
  getPath,
  getProblemStats,
  hasControlTag,
  parsePoint,
  parseSgf,
  playMove,
  visibleComment,
  walkSgf,
  type SgfNode,
  type StoneColor,
} from "./sgf";

export type ValidationSeverity = "error" | "warning";

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: string;
  message: string;
  nodeId?: string;
}

export interface ValidationReport {
  valid: boolean;
  issues: ValidationIssue[];
  root?: SgfNode;
  stats?: ReturnType<typeof getProblemStats>;
}

const ROOT_PROPERTIES = new Set([
  "FF",
  "GM",
  "CA",
  "AP",
  "SZ",
  "C",
  "AB",
  "AW",
  "AE",
  "PL",
  "GN",
  "LB",
  "TR",
  "MA",
]);
const NODE_PROPERTIES = new Set([
  "B",
  "W",
  "C",
  "AB",
  "AW",
  "AE",
  "LB",
  "TR",
  "MA",
]);

function issue(
  severity: ValidationSeverity,
  code: string,
  message: string,
  node?: SgfNode,
): ValidationIssue {
  return { severity, code, message, nodeId: node?.id };
}

function isPointOnBoard(value: string, size: number) {
  const point = parsePoint(value);
  return Boolean(point && point.x >= 0 && point.y >= 0 && point.x < size && point.y < size);
}

function applySetup(board: Map<string, StoneColor>, node: SgfNode) {
  for (const point of expandPointValues(node.properties.AB)) board.set(point, "B");
  for (const point of expandPointValues(node.properties.AW)) board.set(point, "W");
  for (const point of expandPointValues(node.properties.AE)) board.delete(point);
}

export function validateSgf(input: string): ValidationReport {
  const issues: ValidationIssue[] = [];
  let root: SgfNode;

  try {
    root = parseSgf(input);
  } catch (error) {
    return {
      valid: false,
      issues: [
        issue(
          "error",
          "parse-error",
          error instanceof Error ? error.message : "The SGF could not be parsed.",
        ),
      ],
    };
  }

  const nodes = walkSgf(root);
  const size = getBoardSize(root);
  const stats = getProblemStats(root);
  const rightNodes = collectRightNodes(root);
  const setupBlack = expandPointValues(root.properties.AB);
  const setupWhite = expandPointValues(root.properties.AW);

  const declaredBoardSizes = root.properties.SZ ?? [];
  if (declaredBoardSizes.length !== 1 || declaredBoardSizes[0] !== "19") {
    issues.push(
      issue(
        "error",
        "board-size",
        "Every benchmark problem must explicitly declare a 19×19 board with SZ[19].",
        root,
      ),
    );
  }

  if (getMove(root)) {
    issues.push(
      issue(
        "error",
        "root-move",
        "The root must describe a setup position, not contain a played move.",
        root,
      ),
    );
  }

  if (root.properties.C?.length) {
    issues.push(
      issue(
        "error",
        "root-comment",
        "Root comments and written problem instructions are not allowed; the position and first-move color must make the objective clear.",
        root,
      ),
    );
  }

  if (!setupBlack.length || !setupWhite.length) {
    issues.push(
      issue(
        "error",
        "setup-colors",
        "A life-and-death setup must contain both black and white stones at the root.",
        root,
      ),
    );
  }

  const overlap = setupBlack.filter((point) => setupWhite.includes(point));
  if (overlap.length) {
    issues.push(
      issue(
        "error",
        "setup-overlap",
        `Black and white are both set on ${overlap.join(", ")}.`,
        root,
      ),
    );
  }

  if (!rightNodes.length) {
    issues.push(
      issue(
        "error",
        "missing-right",
        "At least one solution node must contain the uppercase RIGHT marker.",
        root,
      ),
    );
  }

  if (stats.setupStoneCount > 48) {
    issues.push(
      issue(
        "warning",
        "large-setup",
        `The setup uses ${stats.setupStoneCount} stones; simple local problems should usually stay at or below 48.`,
        root,
      ),
    );
  }
  if (stats.maxDepth > 14) {
    issues.push(
      issue(
        "error",
        "deep-tree",
        `The longest line is ${stats.maxDepth} moves; the benchmark limit is 14.`,
        root,
      ),
    );
  }
  if (stats.nodeCount > 120) {
    issues.push(
      issue(
        "error",
        "large-tree",
        `The SGF has ${stats.nodeCount} nodes; the benchmark limit is 120.`,
        root,
      ),
    );
  }

  const pointProperties = ["AB", "AW", "AE", "B", "W", "TR", "MA"];
  for (const node of nodes) {
    const moveProperties = [node.properties.B, node.properties.W].filter(Boolean);
    if (node !== root && moveProperties.length !== 1) {
      issues.push(
        issue(
          "error",
          "missing-or-double-move",
          "Every node after the root must contain exactly one B or W move.",
          node,
        ),
      );
    }

    const allowed = node === root ? ROOT_PROPERTIES : NODE_PROPERTIES;
    for (const property of Object.keys(node.properties)) {
      if (!allowed.has(property)) {
        issues.push(
          issue(
            "warning",
            "unsupported-property",
            `Property ${property} is outside the benchmark's supported SGF subset.`,
            node,
          ),
        );
      }
    }

    for (const property of pointProperties) {
      for (const value of expandPointValues(node.properties[property])) {
        if (!isPointOnBoard(value, size)) {
          issues.push(
            issue(
              "error",
              "off-board",
              `${property}[${value}] is outside the ${size}×${size} board.`,
              node,
            ),
          );
        }
      }
    }

    const move = getMove(node);
    if (move && !move.point) {
      issues.push(
        issue("error", "pass-move", "Pass moves are not allowed in benchmark problems.", node),
      );
    }

    const comment = getNodeComment(node);
    if (/(?:CHOICE|FORCE|NOTTHIS)/.test(comment)) {
      issues.push(
        issue(
          "error",
          "website-control",
          "Only RIGHT is supported as a control marker; express all other behavior with explicit SGF branches.",
          node,
        ),
      );
    }
    if (/<\/?(?:script|iframe|object|embed|style|[a-z][^>]*)>/i.test(comment)) {
      issues.push(
        issue(
          "error",
          "html-comment",
          "Comments must be plain text and may not contain HTML or JavaScript.",
          node,
        ),
      );
    }
    if (hasControlTag(node, "RIGHT") && node.children.length) {
      issues.push(
        issue(
          "warning",
          "right-not-terminal",
          "A RIGHT marker should normally end its variation.",
          node,
        ),
      );
    }
  }

  const firstMoves = root.children
    .map(getMove)
    .filter((move): move is NonNullable<ReturnType<typeof getMove>> => Boolean(move));
  const firstMoveColors = new Set(firstMoves.map((move) => move.color));
  if (firstMoveColors.size > 1) {
    issues.push(
      issue(
        "error",
        "mixed-first-color",
        "All first-move variations must use the same player color.",
        root,
      ),
    );
  }
  const protagonist = firstMoves[0]?.color;

  const validateBranch = (
    node: SgfNode,
    board: Map<string, StoneColor>,
    previousColor?: StoneColor,
  ) => {
    const nextBoard = new Map(board);
    applySetup(nextBoard, node);
    const move = getMove(node);

    if (move) {
      if (previousColor === move.color) {
        issues.push(
          issue(
            "error",
            "non-alternating",
            `${move.color} moves twice in succession on this variation.`,
            node,
          ),
        );
      }
      if (move.point) {
        const result = playMove(nextBoard, move, size);
        if (result.occupied) {
          issues.push(
            issue(
              "error",
              "occupied-move",
              `${move.color}[${move.point}] plays on an occupied intersection.`,
              node,
            ),
          );
        }
        if (result.suicide) {
          issues.push(
            issue(
              "error",
              "suicide-move",
              `${move.color}[${move.point}] is suicide under ordinary Go rules.`,
              node,
            ),
          );
        }
      }
    }

    if (
      protagonist &&
      move?.color === protagonist &&
      node.children.length &&
      visibleComment(node)
    ) {
      issues.push(
        issue(
          "warning",
          "hidden-player-comment",
          "Comments on the player's move may be skipped when the reply is automatic; place them on the reply or leaf.",
          node,
        ),
      );
    }

    for (const child of node.children) {
      validateBranch(child, nextBoard, move?.color ?? previousColor);
    }
  };

  const initialBoard = new Map<string, StoneColor>();
  applySetup(initialBoard, root);
  for (const child of root.children) validateBranch(child, initialBoard);

  if (protagonist) {
    const antagonist: StoneColor = protagonist === "B" ? "W" : "B";
    for (const rightNode of rightNodes) {
      const finalMove = getMove(rightNode);
      if (finalMove?.color !== protagonist) {
        issues.push(
          issue(
            "warning",
            "right-ending-color",
            "A correct line should normally end with the protagonist's move.",
            rightNode,
          ),
        );
      }
    }
    for (const leaf of nodes.filter((node) => node !== root && !node.children.length)) {
      const pathHasRight = getPath(leaf).some((node) => hasControlTag(node, "RIGHT"));
      if (!pathHasRight && getMove(leaf)?.color !== antagonist) {
        issues.push(
          issue(
            "warning",
            "wrong-ending-color",
            "A refutation should normally end with the antagonist's move.",
            leaf,
          ),
        );
      }
    }
  }

  return {
    valid: !issues.some((item) => item.severity === "error"),
    issues,
    root,
    stats,
  };
}
