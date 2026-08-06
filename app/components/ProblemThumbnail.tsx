"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  boardAtNode,
  getBoardSize,
  getCrop,
  parsePoint,
  parseSgf,
  type StoneColor,
} from "@/lib/sgf";
import { getGridExtents } from "@/lib/board-geometry";

interface ProblemThumbnailProps {
  sgf: string | null;
}

const CANVAS_SIZE = 112;

export function ProblemThumbnail({ sgf }: ProblemThumbnailProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const preview = useMemo(() => {
    if (!sgf) return null;
    try {
      const root = parseSgf(sgf);
      return {
        board: boardAtNode(root, root).board,
        crop: getCrop(root, 2),
        size: getBoardSize(root),
      };
    } catch {
      return null;
    }
  }, [sgf]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !preview) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const { board, crop, size } = preview;
    const columns = crop.maxX - crop.minX + 1;
    const rows = crop.maxY - crop.minY + 1;
    const leftExtension = crop.minX > 0 ? 0.5 : 0;
    const rightExtension = crop.maxX < size - 1 ? 0.5 : 0;
    const topExtension = crop.minY > 0 ? 0.5 : 0;
    const bottomExtension = crop.maxY < size - 1 ? 0.5 : 0;
    const horizontalSpan = Math.max(1, columns - 1 + leftExtension + rightExtension);
    const verticalSpan = Math.max(1, rows - 1 + topExtension + bottomExtension);
    const margin = 9;
    const cell = Math.min(
      (CANVAS_SIZE - margin * 2) / horizontalSpan,
      (CANVAS_SIZE - margin * 2) / verticalSpan,
    );
    const extentWidth = horizontalSpan * cell;
    const extentHeight = verticalSpan * cell;
    const originX = (CANVAS_SIZE - extentWidth) / 2 + leftExtension * cell;
    const originY = (CANVAS_SIZE - extentHeight) / 2 + topExtension * cell;
    const gridExtents = getGridExtents(crop, size, originX, originY, cell);
    const toCanvas = (x: number, y: number) => ({
      x: originX + (x - crop.minX) * cell,
      y: originY + (y - crop.minY) * cell,
    });

    context.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    const wood = context.createLinearGradient(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    wood.addColorStop(0, "#e7bd76");
    wood.addColorStop(1, "#cf974e");
    context.fillStyle = wood;
    context.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    context.lineCap = "square";
    context.strokeStyle = "rgba(49, 34, 21, 0.76)";
    for (let x = crop.minX; x <= crop.maxX; x += 1) {
      const point = toCanvas(x, crop.minY);
      context.beginPath();
      context.moveTo(point.x, gridExtents.top);
      context.lineTo(point.x, gridExtents.bottom);
      context.lineWidth = x === 0 || x === size - 1 ? 2.2 : 1.15;
      context.stroke();
    }
    for (let y = crop.minY; y <= crop.maxY; y += 1) {
      const point = toCanvas(crop.minX, y);
      context.beginPath();
      context.moveTo(gridExtents.left, point.y);
      context.lineTo(gridExtents.right, point.y);
      context.lineWidth = y === 0 || y === size - 1 ? 2.2 : 1.15;
      context.stroke();
    }

    const drawStone = (coordinate: string, color: StoneColor) => {
      const point = parsePoint(coordinate);
      if (
        !point ||
        point.x < crop.minX ||
        point.x > crop.maxX ||
        point.y < crop.minY ||
        point.y > crop.maxY
      ) {
        return;
      }
      const center = toCanvas(point.x, point.y);
      const radius = Math.max(1.8, cell * 0.46);
      context.save();
      context.shadowColor = "rgba(31, 24, 17, 0.28)";
      context.shadowBlur = Math.max(1.5, radius * 0.22);
      context.shadowOffsetY = Math.max(0.8, radius * 0.12);
      context.beginPath();
      context.arc(center.x, center.y, radius, 0, Math.PI * 2);
      context.fillStyle = color === "B" ? "#111211" : "#faf9f4";
      context.fill();
      context.shadowColor = "transparent";
      context.strokeStyle = color === "B" ? "#050505" : "#9f9b91";
      context.lineWidth = Math.max(0.8, cell * 0.055);
      context.stroke();
      context.restore();
    };

    for (const [coordinate, color] of board) drawStone(coordinate, color);
  }, [preview]);

  if (!preview) {
    return <span className="problem-thumbnail is-empty" aria-hidden="true" />;
  }

  return (
    <canvas
      ref={canvasRef}
      className="problem-thumbnail"
      width={CANVAS_SIZE}
      height={CANVAS_SIZE}
      aria-hidden="true"
    />
  );
}
