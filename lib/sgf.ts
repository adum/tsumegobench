export type StoneColor = "B" | "W";

export type SgfProperties = Record<string, string[]>;

export interface SgfNode {
  id: string;
  properties: SgfProperties;
  children: SgfNode[];
  parent?: SgfNode;
}

export interface Move {
  color: StoneColor;
  point: string;
}

export interface Point {
  x: number;
  y: number;
}

export interface Crop {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface BoardPosition {
  board: Map<string, StoneColor>;
  lastMove?: Move;
  captures: number;
}

const CONTROL_TAGS = ["RIGHT"] as const;

class SgfParser {
  private index = 0;
  private nodeIndex = 0;

  constructor(private readonly input: string) {}

  parse(): SgfNode {
    this.skipWhitespace();
    const root = this.parseGameTree();
    this.skipWhitespace();
    if (this.index !== this.input.length) {
      throw new Error(`Unexpected content at character ${this.index + 1}.`);
    }
    return root;
  }

  private parseGameTree(): SgfNode {
    this.expect("(");
    this.skipWhitespace();

    let first: SgfNode | undefined;
    let previous: SgfNode | undefined;

    while (this.peek() === ";") {
      const node = this.parseNode();
      if (!first) first = node;
      if (previous) this.attach(previous, node);
      previous = node;
      this.skipWhitespace();
    }

    if (!first || !previous) {
      throw new Error(`A game tree at character ${this.index + 1} has no nodes.`);
    }

    while (this.peek() === "(") {
      this.attach(previous, this.parseGameTree());
      this.skipWhitespace();
    }

    this.expect(")");
    return first;
  }

  private parseNode(): SgfNode {
    this.expect(";");
    const properties: SgfProperties = {};
    this.skipWhitespace();

    while (/[A-Za-z]/.test(this.peek() ?? "")) {
      const identifier = this.parseIdentifier();
      this.skipWhitespace();
      const values: string[] = [];
      while (this.peek() === "[") {
        values.push(this.parseValue());
        this.skipWhitespace();
      }
      if (!values.length) {
        throw new Error(
          `Property ${identifier} at character ${this.index + 1} has no value.`,
        );
      }
      properties[identifier] = [...(properties[identifier] ?? []), ...values];
    }

    return {
      id: `n${this.nodeIndex++}`,
      properties,
      children: [],
    };
  }

  private parseIdentifier(): string {
    const start = this.index;
    while (/[A-Za-z]/.test(this.peek() ?? "")) this.index += 1;
    return this.input.slice(start, this.index).toUpperCase();
  }

  private parseValue(): string {
    this.expect("[");
    let value = "";

    while (this.index < this.input.length) {
      const character = this.input[this.index++];
      if (character === "]") return value;
      if (character !== "\\") {
        value += character;
        continue;
      }

      if (this.index >= this.input.length) break;
      const escaped = this.input[this.index++];
      if (escaped === "\r") {
        if (this.peek() === "\n") this.index += 1;
      } else if (escaped !== "\n") {
        value += escaped;
      }
    }

    throw new Error("Unterminated SGF property value.");
  }

  private attach(parent: SgfNode, child: SgfNode) {
    child.parent = parent;
    parent.children.push(child);
  }

  private skipWhitespace() {
    while (/\s/.test(this.peek() ?? "")) this.index += 1;
  }

  private peek() {
    return this.input[this.index];
  }

  private expect(character: string) {
    if (this.input[this.index] !== character) {
      throw new Error(
        `Expected ${JSON.stringify(character)} at character ${this.index + 1}.`,
      );
    }
    this.index += 1;
  }
}

export function parseSgf(input: string): SgfNode {
  if (!input.trim()) throw new Error("The SGF is empty.");
  return new SgfParser(input).parse();
}

/**
 * Remove C properties from the root node while preserving the original SGF
 * formatting and every comment in the solution tree.
 */
export function stripRootComment(input: string): string {
  let index = input.charCodeAt(0) === 0xfeff ? 1 : 0;
  while (/\s/.test(input[index] ?? "")) index += 1;
  if (input[index] !== "(") return input;

  index += 1;
  while (/\s/.test(input[index] ?? "")) index += 1;
  if (input[index] !== ";") return input;
  index += 1;

  const commentSpans: Array<[number, number]> = [];
  while (index < input.length) {
    while (/\s/.test(input[index] ?? "")) index += 1;
    if ([";", "(", ")"].includes(input[index] ?? "")) break;

    const propertyStart = index;
    while (/[A-Za-z]/.test(input[index] ?? "")) index += 1;
    const identifier = input.slice(propertyStart, index).toUpperCase();
    if (!identifier) break;

    while (/\s/.test(input[index] ?? "")) index += 1;
    let hasValue = false;
    while (input[index] === "[") {
      hasValue = true;
      index += 1;
      while (index < input.length) {
        const character = input[index++];
        if (character === "\\") {
          if (index < input.length) index += 1;
        } else if (character === "]") {
          break;
        }
      }
      while (/\s/.test(input[index] ?? "")) index += 1;
    }

    if (identifier === "C" && hasValue) commentSpans.push([propertyStart, index]);
  }

  return commentSpans
    .reverse()
    .reduce(
      (sgf, [start, end]) => `${sgf.slice(0, start)}${sgf.slice(end)}`,
      input,
    );
}

export function walkSgf(root: SgfNode): SgfNode[] {
  const nodes: SgfNode[] = [];
  const visit = (node: SgfNode) => {
    nodes.push(node);
    node.children.forEach(visit);
  };
  visit(root);
  return nodes;
}

export function getMove(node: SgfNode): Move | undefined {
  if (node.properties.B) return { color: "B", point: node.properties.B[0] ?? "" };
  if (node.properties.W) return { color: "W", point: node.properties.W[0] ?? "" };
  return undefined;
}

export function getBoardSize(root: SgfNode): number {
  const raw = root.properties.SZ?.[0] ?? "19";
  const squareSize = raw.split(":")[0];
  const size = Number.parseInt(squareSize, 10);
  return Number.isFinite(size) && size > 0 ? size : 19;
}

export function getNodeComment(node: SgfNode): string {
  return node.properties.C?.join("\n") ?? "";
}

export function hasControlTag(node: SgfNode, tag: (typeof CONTROL_TAGS)[number]) {
  return getNodeComment(node).toUpperCase().includes(tag);
}

export function subtreeHasRight(node: SgfNode): boolean {
  return hasControlTag(node, "RIGHT") || node.children.some(subtreeHasRight);
}

export function visibleComment(node: SgfNode): string {
  let comment = getNodeComment(node);
  for (const tag of CONTROL_TAGS) {
    comment = comment.replaceAll(tag, "");
  }
  return comment.replace(/\s+/g, " ").trim();
}

export function collectRightNodes(root: SgfNode): SgfNode[] {
  return walkSgf(root).filter((node) => hasControlTag(node, "RIGHT"));
}

export function getPath(node: SgfNode): SgfNode[] {
  const path: SgfNode[] = [];
  let current: SgfNode | undefined = node;
  while (current) {
    path.unshift(current);
    current = current.parent;
  }
  return path;
}

export function parsePoint(value: string): Point | undefined {
  if (value.length !== 2) return undefined;
  const toIndex = (character: string) => {
    const code = character.charCodeAt(0);
    if (code >= 97 && code <= 122) return code - 97;
    if (code >= 65 && code <= 90) return code - 65 + 26;
    return Number.NaN;
  };
  const x = toIndex(value[0]);
  const y = toIndex(value[1]);
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : undefined;
}

export function pointToSgf(point: Point): string {
  const toCharacter = (value: number) =>
    value < 26
      ? String.fromCharCode(97 + value)
      : String.fromCharCode(65 + value - 26);
  return `${toCharacter(point.x)}${toCharacter(point.y)}`;
}

export function pointToHuman(value: string, boardSize = 19): string {
  const point = parsePoint(value);
  if (!point) return "pass";
  const alphabet = "ABCDEFGHJKLMNOPQRSTUVWXYZ";
  return `${alphabet[point.x] ?? "?"}${boardSize - point.y}`;
}

export function expandPointValues(values: string[] = []): string[] {
  const expanded: string[] = [];
  for (const value of values) {
    const [fromValue, toValue] = value.split(":");
    const from = parsePoint(fromValue);
    const to = toValue ? parsePoint(toValue) : undefined;
    if (!from) continue;
    if (!to) {
      expanded.push(pointToSgf(from));
      continue;
    }
    for (let x = Math.min(from.x, to.x); x <= Math.max(from.x, to.x); x += 1) {
      for (let y = Math.min(from.y, to.y); y <= Math.max(from.y, to.y); y += 1) {
        expanded.push(pointToSgf({ x, y }));
      }
    }
  }
  return expanded;
}

export function getProblemStats(root: SgfNode) {
  const nodes = walkSgf(root);
  let maxDepth = 0;
  let variationPoints = 0;

  const visit = (node: SgfNode, depth: number) => {
    const nextDepth = depth + (getMove(node) ? 1 : 0);
    maxDepth = Math.max(maxDepth, nextDepth);
    if (node.children.length > 1) variationPoints += 1;
    node.children.forEach((child) => visit(child, nextDepth));
  };
  visit(root, 0);

  return {
    nodeCount: nodes.length,
    moveCount: nodes.filter(getMove).length,
    maxDepth,
    variationPoints,
    rightCount: collectRightNodes(root).length,
    setupStoneCount:
      expandPointValues(root.properties.AB).length +
      expandPointValues(root.properties.AW).length,
  };
}

function neighbors(point: Point, size: number): Point[] {
  return [
    { x: point.x - 1, y: point.y },
    { x: point.x + 1, y: point.y },
    { x: point.x, y: point.y - 1 },
    { x: point.x, y: point.y + 1 },
  ].filter(({ x, y }) => x >= 0 && y >= 0 && x < size && y < size);
}

function groupAt(board: Map<string, StoneColor>, start: Point, size: number) {
  const color = board.get(pointToSgf(start));
  const stones = new Set<string>();
  const liberties = new Set<string>();
  if (!color) return { stones, liberties };

  const queue = [start];
  while (queue.length) {
    const point = queue.pop()!;
    const key = pointToSgf(point);
    if (stones.has(key)) continue;
    stones.add(key);
    for (const neighbor of neighbors(point, size)) {
      const neighborKey = pointToSgf(neighbor);
      const neighborColor = board.get(neighborKey);
      if (!neighborColor) liberties.add(neighborKey);
      else if (neighborColor === color && !stones.has(neighborKey)) queue.push(neighbor);
    }
  }
  return { stones, liberties };
}

export function playMove(
  board: Map<string, StoneColor>,
  move: Move,
  size: number,
): { captures: number; occupied: boolean; suicide: boolean } {
  const point = parsePoint(move.point);
  if (!point) return { captures: 0, occupied: false, suicide: false };
  const key = pointToSgf(point);
  if (board.has(key)) return { captures: 0, occupied: true, suicide: false };

  board.set(key, move.color);
  const opponent: StoneColor = move.color === "B" ? "W" : "B";
  let captures = 0;

  for (const neighbor of neighbors(point, size)) {
    if (board.get(pointToSgf(neighbor)) !== opponent) continue;
    const group = groupAt(board, neighbor, size);
    if (group.liberties.size === 0) {
      for (const stone of group.stones) board.delete(stone);
      captures += group.stones.size;
    }
  }

  const ownGroup = groupAt(board, point, size);
  const suicide = ownGroup.liberties.size === 0;
  if (suicide) {
    for (const stone of ownGroup.stones) board.delete(stone);
  }
  return { captures, occupied: false, suicide };
}

function applySetup(board: Map<string, StoneColor>, node: SgfNode) {
  for (const point of expandPointValues(node.properties.AB)) board.set(point, "B");
  for (const point of expandPointValues(node.properties.AW)) board.set(point, "W");
  for (const point of expandPointValues(node.properties.AE)) board.delete(point);
}

export function boardAtNode(root: SgfNode, selected: SgfNode): BoardPosition {
  const board = new Map<string, StoneColor>();
  const size = getBoardSize(root);
  let lastMove: Move | undefined;
  let captures = 0;

  for (const node of getPath(selected)) {
    applySetup(board, node);
    const move = getMove(node);
    if (move) {
      captures += playMove(board, move, size).captures;
      lastMove = move;
    }
  }
  return { board, lastMove, captures };
}

export function collectAllPoints(root: SgfNode): Point[] {
  const points: Point[] = [];
  for (const node of walkSgf(root)) {
    for (const property of ["AB", "AW", "AE", "B", "W", "TR", "MA"] as const) {
      for (const value of expandPointValues(node.properties[property])) {
        const point = parsePoint(value);
        if (point) points.push(point);
      }
    }
    for (const label of node.properties.LB ?? []) {
      const point = parsePoint(label.split(":", 1)[0]);
      if (point) points.push(point);
    }
  }
  return points;
}

export function getCrop(root: SgfNode, padding = 1): Crop {
  const size = getBoardSize(root);
  const points = collectAllPoints(root);
  if (!points.length) return { minX: 0, maxX: size - 1, minY: 0, maxY: size - 1 };

  const valuesX = points.map((point) => point.x);
  const valuesY = points.map((point) => point.y);
  let minX = Math.max(0, Math.min(...valuesX) - padding);
  let maxX = Math.min(size - 1, Math.max(...valuesX) + padding);
  let minY = Math.max(0, Math.min(...valuesY) - padding);
  let maxY = Math.min(size - 1, Math.max(...valuesY) + padding);

  if (Math.min(...valuesX) <= 2) minX = 0;
  if (Math.max(...valuesX) >= size - 3) maxX = size - 1;
  if (Math.min(...valuesY) <= 2) minY = 0;
  if (Math.max(...valuesY) >= size - 3) maxY = size - 1;

  const ensureSpan = (min: number, max: number): [number, number] => {
    while (max - min < 4 && (min > 0 || max < size - 1)) {
      if (min > 0) min -= 1;
      if (max - min < 4 && max < size - 1) max += 1;
    }
    return [min, max];
  };
  [minX, maxX] = ensureSpan(minX, maxX);
  [minY, maxY] = ensureSpan(minY, maxY);
  return { minX, maxX, minY, maxY };
}

type Transform = (point: Point) => Point;

const TRANSFORMS: Transform[] = [
  ({ x, y }) => ({ x, y }),
  ({ x, y }) => ({ x: -x, y }),
  ({ x, y }) => ({ x, y: -y }),
  ({ x, y }) => ({ x: -x, y: -y }),
  ({ x, y }) => ({ x: y, y: x }),
  ({ x, y }) => ({ x: -y, y: x }),
  ({ x, y }) => ({ x: y, y: -x }),
  ({ x, y }) => ({ x: -y, y: -x }),
];

function canonicalCandidates(root: SgfNode, rightNode?: SgfNode): string[] {
  const includedNodes = rightNode ? new Set(getPath(rightNode)) : undefined;
  const allPoints = walkSgf(root)
    .filter((node) => !includedNodes || includedNodes.has(node) || node === root)
    .flatMap((node) => {
      const values = [
        ...expandPointValues(node.properties.AB),
        ...expandPointValues(node.properties.AW),
      ];
      const move = getMove(node);
      if (move?.point) values.push(move.point);
      return values.map(parsePoint).filter((point): point is Point => Boolean(point));
    });

  const serialize = (
    transform: Transform,
    flipColors: boolean,
    featureOnly: boolean,
  ) => {
    const transformed = allPoints.map(transform);
    const minX = Math.min(...transformed.map((point) => point.x));
    const minY = Math.min(...transformed.map((point) => point.y));
    const mapPoint = (value: string) => {
      const point = parsePoint(value);
      if (!point) return "pass";
      const mapped = transform(point);
      return `${mapped.x - minX},${mapped.y - minY}`;
    };
    const mapColor = (color: StoneColor): StoneColor =>
      flipColors ? (color === "B" ? "W" : "B") : color;

    const setup = (["B", "W"] as StoneColor[])
      .flatMap((color) => {
        const property = color === "B" ? "AB" : "AW";
        return expandPointValues(root.properties[property]).map(
          (point) => `S${mapColor(color)}:${mapPoint(point)}`,
        );
      })
      .sort();

    if (rightNode) {
      const moves = getPath(rightNode)
        .map(getMove)
        .filter((move): move is Move => Boolean(move))
        .map(
          (move, index) =>
            `M${index + 1}${mapColor(move.color)}:${mapPoint(move.point)}`,
        );
      return [...setup, ...moves].sort().join("|");
    }

    const serializeNode = (node: SgfNode): string => {
      const move = getMove(node);
      const status = CONTROL_TAGS.filter((tag) => hasControlTag(node, tag)).join("+");
      const head = move
        ? `${mapColor(move.color)}:${mapPoint(move.point)}${status ? `:${status}` : ""}`
        : "ROOT";
      const children = node.children.map(serializeNode).sort();
      return `${head}${children.length ? `{${children.join(",")}}` : ""}`;
    };

    return `${featureOnly ? "" : `${setup.join("|")}#`}${serializeNode(root)}`;
  };

  if (!allPoints.length) return [""];
  return TRANSFORMS.flatMap((transform) => [
    serialize(transform, false, false),
    serialize(transform, true, false),
  ]);
}

export function canonicalProblemFingerprint(root: SgfNode): string {
  return canonicalCandidates(root).sort()[0];
}

export function canonicalRightShapes(root: SgfNode): string[] {
  return collectRightNodes(root)
    .map((rightNode) => canonicalCandidates(root, rightNode).sort()[0])
    .sort();
}

export function shapeSimilarity(first: string, second: string): number {
  const firstSet = new Set(first.split("|").filter(Boolean));
  const secondSet = new Set(second.split("|").filter(Boolean));
  if (!firstSet.size && !secondSet.size) return 1;
  let intersection = 0;
  for (const token of firstSet) if (secondSet.has(token)) intersection += 1;
  return intersection / (firstSet.size + secondSet.size - intersection);
}
