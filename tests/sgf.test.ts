import assert from "node:assert/strict";
import test from "node:test";
import {
  boardAtNode,
  canonicalProblemFingerprint,
  collectRightNodes,
  parseSgf,
  stripRootComment,
  subtreeHasRight,
  visibleComment,
  walkSgf,
} from "../lib/sgf";
import { validateSgf } from "../lib/validate-sgf";

const simple =
  "(;FF[4]GM[1]SZ[19]AB[aa][ba][ca]AW[ab][bb](;B[cb];W[cc];B[bc]C[RIGHT])(;B[bc];W[cb]))";

test("parses variations and locates RIGHT nodes", () => {
  const root = parseSgf(simple);
  assert.equal(root.children.length, 2);
  assert.equal(walkSgf(root).length, 6);
  assert.equal(collectRightNodes(root).length, 1);
  assert.equal(subtreeHasRight(root.children[0]), true);
  assert.equal(subtreeHasRight(root.children[1]), false);
});

test("replays captures along a selected path", () => {
  const root = parseSgf("(;SZ[19]AB[ba][ab][cb]AW[bb];B[bc]C[RIGHT])");
  const leaf = root.children[0];
  const position = boardAtNode(root, leaf);
  assert.equal(position.board.has("bb"), false);
  assert.equal(position.captures, 1);
});

test("canonical fingerprint ignores translation and color reversal", () => {
  const first = parseSgf("(;SZ[19]AB[aa][ba]AW[ab];B[bb]C[RIGHT])");
  const second = parseSgf("(;SZ[19]AW[dd][ed]AB[de];W[ee]C[RIGHT])");
  assert.equal(canonicalProblemFingerprint(first), canonicalProblemFingerprint(second));
});

test("strips only the written instruction from the root", () => {
  const cleaned = stripRootComment(
    "(;SZ[19]C[White to live \\] unconditionally]AB[aa]AW[bb](;W[cc]C[RIGHT]))",
  );
  const root = parseSgf(cleaned);
  assert.equal(visibleComment(root), "");
  assert.equal(visibleComment(root.children[0]), "");
  assert.equal(collectRightNodes(root).length, 1);
});

test("validator catches a pass and missing RIGHT", () => {
  const report = validateSgf("(;SZ[19]AB[aa]AW[bb];B[])");
  assert.equal(report.valid, false);
  assert.ok(report.issues.some((issue) => issue.code === "pass-move"));
  assert.ok(report.issues.some((issue) => issue.code === "missing-right"));
});

test("validator rejects written instructions at the root", () => {
  const report = validateSgf(
    "(;SZ[19]AB[aa]AW[bb]C[Find the best result](;B[ab]C[RIGHT]))",
  );
  assert.equal(report.valid, false);
  assert.ok(report.issues.some((issue) => issue.code === "root-comment"));
});

test("validator requires an explicit 19 by 19 board", () => {
  for (const sgf of [
    "(;AB[aa]AW[bb](;B[ab]C[RIGHT]))",
    "(;SZ[9]AB[aa]AW[bb](;B[ab]C[RIGHT]))",
    "(;SZ[13]AB[aa]AW[bb](;B[ab]C[RIGHT]))",
  ]) {
    const report = validateSgf(sgf);
    assert.equal(report.valid, false);
    assert.ok(report.issues.some((issue) => issue.code === "board-size"));
  }

  const report = validateSgf("(;SZ[19]AB[aa]AW[bb](;B[ab]C[RIGHT]))");
  assert.ok(!report.issues.some((issue) => issue.code === "board-size"));
});

test("validator rejects website-specific playback controls", () => {
  for (const marker of ["CHOICE", "FORCE", "NOTTHIS"]) {
    const report = validateSgf(
      `(;SZ[19]AB[aa]AW[bb](;B[ab]C[RIGHT ${marker}]))`,
    );
    assert.equal(report.valid, false);
    assert.ok(report.issues.some((issue) => issue.code === "website-control"));
  }
});
