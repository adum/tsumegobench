import assert from "node:assert/strict";
import test from "node:test";
import { getGridExtents } from "../lib/board-geometry";

test("partial board crops stay closed only on true board edges", () => {
  assert.deepEqual(getGridExtents({ minX: 0, maxX: 7, minY: 0, maxY: 7 }, 19, 40, 50, 20), {
    left: 40,
    right: 190,
    top: 50,
    bottom: 200,
  });

  assert.deepEqual(getGridExtents({ minX: 5, maxX: 9, minY: 6, maxY: 10 }, 19, 40, 50, 20), {
    left: 30,
    right: 130,
    top: 40,
    bottom: 140,
  });
});

test("a full board keeps its four physical edges closed", () => {
  assert.deepEqual(getGridExtents({ minX: 0, maxX: 18, minY: 0, maxY: 18 }, 19, 30, 30, 20), {
    left: 30,
    right: 390,
    top: 30,
    bottom: 390,
  });
});
