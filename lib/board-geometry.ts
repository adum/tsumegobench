export interface BoardCrop {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface GridExtents {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export function getGridExtents(
  crop: BoardCrop,
  boardSize: number,
  originX: number,
  originY: number,
  cell: number,
): GridExtents {
  const halfCell = cell * 0.5;
  const lastX = originX + (crop.maxX - crop.minX) * cell;
  const lastY = originY + (crop.maxY - crop.minY) * cell;

  return {
    left: originX - (crop.minX > 0 ? halfCell : 0),
    right: lastX + (crop.maxX < boardSize - 1 ? halfCell : 0),
    top: originY - (crop.minY > 0 ? halfCell : 0),
    bottom: lastY + (crop.maxY < boardSize - 1 ? halfCell : 0),
  };
}
