"use client";

import {
  useEffect,
  useMemo,
  useRef,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  boardAtNode,
  expandPointValues,
  getBoardSize,
  getCrop,
  getMove,
  getPath,
  parsePoint,
  pointToHuman,
  subtreeHasRight,
  type SgfNode,
  type StoneColor,
} from "@/lib/sgf";
import { getGridExtents } from "@/lib/board-geometry";

interface GoBoardProps {
  root: SgfNode;
  selected: SgfNode;
  onSelect: (node: SgfNode) => void;
  variationLegendId?: string;
}

interface VariationTarget {
  node: SgfNode;
  x: number;
  y: number;
  radius: number;
}

export function GoBoard({
  root,
  selected,
  onSelect,
  variationLegendId = "board-variation-legend",
}: GoBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const variationTargetsRef = useRef<VariationTarget[]>([]);
  const crop = useMemo(() => getCrop(root, 1), [root]);
  const boardPosition = useMemo(() => boardAtNode(root, selected), [root, selected]);
  const variationNodes = useMemo(
    () => selected.children.filter((child) => Boolean(getMove(child)?.point)),
    [selected],
  );
  const variationSummary = useMemo(() => {
    return {
      total: variationNodes.length,
      withResult: variationNodes.filter(subtreeHasRight).length,
    };
  }, [variationNodes]);
  const columns = crop.maxX - crop.minX + 1;
  const rows = crop.maxY - crop.minY + 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const draw = () => {
      variationTargetsRef.current = [];
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (!width || !height) return;

      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      const context = canvas.getContext("2d");
      if (!context) return;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);

      const size = getBoardSize(root);
      const position = boardAtNode(root, selected);
      const coordinateRoom = 24;
      const cell = Math.min(
        (width - coordinateRoom * 2) / Math.max(columns, 1),
        (height - coordinateRoom * 2) / Math.max(rows, 1),
      );
      const gridWidth = cell * Math.max(columns - 1, 1);
      const gridHeight = cell * Math.max(rows - 1, 1);
      const originX = (width - gridWidth) / 2;
      const originY = (height - gridHeight) / 2;
      const gridExtents = getGridExtents(crop, size, originX, originY, cell);
      const toCanvas = (x: number, y: number) => ({
        x: originX + (x - crop.minX) * cell,
        y: originY + (y - crop.minY) * cell,
      });

      const wood = context.createLinearGradient(0, 0, width, height);
      wood.addColorStop(0, "#e8bd72");
      wood.addColorStop(0.55, "#dba85d");
      wood.addColorStop(1, "#cc9348");
      context.fillStyle = wood;
      context.fillRect(0, 0, width, height);

      context.save();
      context.globalAlpha = 0.13;
      context.strokeStyle = "#8b582d";
      context.lineWidth = 0.7;
      for (let line = 0; line < 18; line += 1) {
        const y = ((line + 0.5) / 18) * height;
        context.beginPath();
        for (let x = 0; x <= width; x += 12) {
          const drift = Math.sin(x * 0.036 + line * 1.7) * 2.2;
          if (x === 0) context.moveTo(x, y + drift);
          else context.lineTo(x, y + drift);
        }
        context.stroke();
      }
      context.restore();

      context.lineCap = "square";
      for (let x = crop.minX; x <= crop.maxX; x += 1) {
        const lineX = toCanvas(x, crop.minY).x;
        context.beginPath();
        context.moveTo(lineX, gridExtents.top);
        context.lineTo(lineX, gridExtents.bottom);
        context.strokeStyle = "rgba(48, 35, 22, 0.78)";
        context.lineWidth = x === 0 || x === size - 1 ? 1.8 : 0.85;
        context.stroke();
      }
      for (let y = crop.minY; y <= crop.maxY; y += 1) {
        const lineY = toCanvas(crop.minX, y).y;
        context.beginPath();
        context.moveTo(gridExtents.left, lineY);
        context.lineTo(gridExtents.right, lineY);
        context.strokeStyle = "rgba(48, 35, 22, 0.78)";
        context.lineWidth = y === 0 || y === size - 1 ? 1.8 : 0.85;
        context.stroke();
      }

      const starSets: Record<number, number[]> = {
        9: [2, 4, 6],
        13: [3, 6, 9],
        19: [3, 9, 15],
      };
      for (const x of starSets[size] ?? []) {
        for (const y of starSets[size] ?? []) {
          if (x < crop.minX || x > crop.maxX || y < crop.minY || y > crop.maxY) continue;
          const point = toCanvas(x, y);
          context.beginPath();
          context.arc(point.x, point.y, Math.max(1.8, cell * 0.085), 0, Math.PI * 2);
          context.fillStyle = "#312117";
          context.fill();
        }
      }

      context.fillStyle = "rgba(57, 38, 22, 0.68)";
      context.font = `600 ${Math.min(11, Math.max(8, cell * 0.25))}px Geist, sans-serif`;
      context.textAlign = "center";
      context.textBaseline = "middle";
      const coordinateOffset = cell * 0.5 + coordinateRoom * 0.5;
      const alphabet = "ABCDEFGHJKLMNOPQRSTUVWXYZ";
      for (let x = crop.minX; x <= crop.maxX; x += 1) {
        const point = toCanvas(x, crop.maxY);
        context.fillText(
          alphabet[x] ?? "?",
          point.x,
          Math.min(height - 7, point.y + coordinateOffset),
        );
      }
      context.textAlign = "right";
      for (let y = crop.minY; y <= crop.maxY; y += 1) {
        const point = toCanvas(crop.minX, y);
        context.fillText(
          String(size - y),
          Math.max(12, point.x - coordinateOffset),
          point.y,
        );
      }

      const drawStone = (coordinate: string, color: StoneColor) => {
        const point = parsePoint(coordinate);
        if (!point) return;
        if (
          point.x < crop.minX ||
          point.x > crop.maxX ||
          point.y < crop.minY ||
          point.y > crop.maxY
        ) {
          return;
        }
        const center = toCanvas(point.x, point.y);
        // Go stones should almost fill the distance between intersections.
        const radius = cell * 0.46;
        context.save();
        context.shadowColor = "rgba(36, 24, 15, 0.35)";
        context.shadowBlur = Math.max(2, radius * 0.24);
        context.shadowOffsetY = Math.max(1, radius * 0.14);
        context.beginPath();
        context.arc(center.x, center.y, radius, 0, Math.PI * 2);
        const stone = context.createRadialGradient(
          center.x - radius * 0.28,
          center.y - radius * 0.32,
          radius * 0.08,
          center.x,
          center.y,
          radius,
        );
        if (color === "B") {
          stone.addColorStop(0, "#646462");
          stone.addColorStop(0.32, "#252524");
          stone.addColorStop(1, "#050505");
        } else {
          stone.addColorStop(0, "#ffffff");
          stone.addColorStop(0.7, "#eeeae0");
          stone.addColorStop(1, "#c9c3b8");
        }
        context.fillStyle = stone;
        context.fill();
        context.shadowColor = "transparent";
        context.strokeStyle = color === "B" ? "#020202" : "#aaa397";
        context.lineWidth = 0.8;
        context.stroke();
        context.restore();
      };

      for (const [coordinate, color] of position.board) drawStone(coordinate, color);

      const markupNodes = [root, ...getPath(selected).slice(-1)];
      for (const node of markupNodes) {
        for (const coordinate of expandPointValues(node.properties.TR)) {
          const point = parsePoint(coordinate);
          if (!point) continue;
          const center = toCanvas(point.x, point.y);
          const color = position.board.get(coordinate) === "B" ? "#f7f3ea" : "#171714";
          const radius = cell * 0.22;
          context.beginPath();
          context.moveTo(center.x, center.y - radius);
          context.lineTo(center.x + radius, center.y + radius * 0.8);
          context.lineTo(center.x - radius, center.y + radius * 0.8);
          context.closePath();
          context.strokeStyle = color;
          context.lineWidth = 1.7;
          context.stroke();
        }
        for (const coordinate of expandPointValues(node.properties.MA)) {
          const point = parsePoint(coordinate);
          if (!point) continue;
          const center = toCanvas(point.x, point.y);
          const color = position.board.get(coordinate) === "B" ? "#f7f3ea" : "#171714";
          const radius = cell * 0.2;
          context.strokeStyle = color;
          context.lineWidth = 1.7;
          context.strokeRect(center.x - radius, center.y - radius, radius * 2, radius * 2);
        }
      }

      for (const child of selected.children) {
        const move = getMove(child);
        const point = move?.point ? parsePoint(move.point) : undefined;
        if (
          !move?.point ||
          !point ||
          position.board.has(move.point) ||
          point.x < crop.minX ||
          point.x > crop.maxX ||
          point.y < crop.minY ||
          point.y > crop.maxY
        ) {
          continue;
        }

        const center = toCanvas(point.x, point.y);
        const hasResult = subtreeHasRight(child);
        const markerColor = hasResult ? "#4f8218" : "#c62622";
        context.save();
        context.beginPath();
        context.arc(center.x, center.y, cell * 0.23, 0, Math.PI * 2);
        context.strokeStyle = markerColor;
        context.lineWidth = Math.max(2.5, cell * 0.055);
        context.stroke();
        if (hasResult) {
          context.beginPath();
          context.arc(center.x, center.y, cell * 0.085, 0, Math.PI * 2);
          context.fillStyle = markerColor;
          context.fill();
        }
        context.restore();
        variationTargetsRef.current.push({
          node: child,
          x: center.x,
          y: center.y,
          radius: cell * 0.32,
        });
      }

      if (position.lastMove?.point) {
        const point = parsePoint(position.lastMove.point);
        if (point) {
          const center = toCanvas(point.x, point.y);
          context.beginPath();
          context.arc(center.x, center.y, Math.max(2.4, cell * 0.11), 0, Math.PI * 2);
          context.fillStyle = position.lastMove.color === "B" ? "#f8f4e8" : "#b23d2d";
          context.fill();
        }
      }
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [columns, crop, root, rows, selected]);

  const findVariationTarget = (
    canvas: HTMLCanvasElement,
    clientX: number,
    clientY: number,
  ) => {
    const bounds = canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return undefined;
    const x = (clientX - bounds.left) * (canvas.clientWidth / bounds.width);
    const y = (clientY - bounds.top) * (canvas.clientHeight / bounds.height);
    return variationTargetsRef.current.find(
      (target) => Math.hypot(x - target.x, y - target.y) <= target.radius,
    );
  };

  const handleClick = (event: ReactMouseEvent<HTMLCanvasElement>) => {
    const target = findVariationTarget(event.currentTarget, event.clientX, event.clientY);
    if (target) onSelect(target.node);
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const target = findVariationTarget(event.currentTarget, event.clientX, event.clientY);
    event.currentTarget.style.cursor = target ? "pointer" : "default";
  };

  return (
    <>
      <canvas
        ref={canvasRef}
        className="go-board-canvas"
        style={{ aspectRatio: `${Math.max(columns, 5)} / ${Math.max(rows, 5)}` }}
        onClick={handleClick}
        onPointerMove={handlePointerMove}
        onPointerLeave={(event) => {
          event.currentTarget.style.cursor = "default";
        }}
        title={variationSummary.total ? "Click a colored marker to select that variation." : undefined}
        aria-describedby={variationSummary.total ? variationLegendId : undefined}
        aria-label={
          `${boardPosition.lastMove
            ? `Go board showing ${pointToHuman(
                boardPosition.lastMove.point,
                getBoardSize(root),
              )} as the latest move`
            : "Go board setup position"}${
            variationSummary.total
              ? `; ${variationSummary.total} next variations, ${variationSummary.withResult} leading to RIGHT`
              : ""
          }`
        }
      />
      {variationNodes.length > 0 && (
        <div className="sr-only" aria-label="Available board variations">
          {variationNodes.map((node) => {
            const move = getMove(node)!;
            return (
              <button type="button" key={node.id} onClick={() => onSelect(node)}>
                {move.color === "B" ? "Black" : "White"} {pointToHuman(move.point, getBoardSize(root))}
                {subtreeHasRight(node) ? ", leads to RIGHT" : ", no RIGHT"}
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}
