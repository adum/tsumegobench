import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { findBuiltInSetupDuplicate } from "../lib/common-setup-duplicates";
import { checkProblemDuplicates, loadDuplicateCorpus } from "../lib/duplicate-check";
import { parseSgf } from "../lib/sgf";

const commonSetup =
  "(;FF[4]GM[1]CA[UTF-8]SZ[19]AB[aq][bq][cq][dq][eq][er][es]AW[ar][br][cr][dr][ds](;B[bs]C[RIGHT])(;B[as];W[bs])(;B[cs];W[bs]))";
const commonSetupTwo =
  "(;FF[4]GM[1]CA[UTF-8]SZ[19]AB[pa][pb][pc][pd][qd][qe][re][se]AW[qa][qb][qc][rc][rd][sd](;B[sb]C[RIGHT])(;B[sa];W[sb])(;B[sc];W[sb])(;B[ra];W[sb])(;B[rb];W[sb]))";
const last = 18;
const setupTransforms = [
  ([x, y]: number[]) => [x, y],
  ([x, y]: number[]) => [last - y, x],
  ([x, y]: number[]) => [last - x, last - y],
  ([x, y]: number[]) => [y, last - x],
  ([x, y]: number[]) => [last - x, y],
  ([x, y]: number[]) => [x, last - y],
  ([x, y]: number[]) => [y, x],
  ([x, y]: number[]) => [last - y, last - x],
];

function assertAllSetupVariants(id: string, black: number[][], white: number[][]) {
  const property = (name: string, points: number[][], transform: (point: number[]) => number[]) =>
    `${name}${points.map((point) => {
      const [x, y] = transform(point);
      return `[${String.fromCharCode(97 + x)}${String.fromCharCode(97 + y)}]`;
    }).join("")}`;

  for (const transform of setupTransforms) {
    for (const reverseColors of [false, true]) {
      const candidateBlack = reverseColors ? white : black;
      const candidateWhite = reverseColors ? black : white;
      const sgf = `(;SZ[19]${property("AB", candidateBlack, transform)}${property("AW", candidateWhite, transform)})`;
      assert.equal(findBuiltInSetupDuplicate(parseSgf(sgf))?.id, id);
    }
  }
}

test("local duplicate evaluation rejects a copied reference without using the network", async () => {
  const sgf = await readFile(
    "examples/canonical-life-and-death/gp-18843.sgf",
    "utf8",
  );
  const report = await checkProblemDuplicates(sgf, parseSgf(sgf), await loadDuplicateCorpus(), {
    remote: false,
  });

  assert.equal(report.status, "fail");
  assert.equal(report.exactLocalMatch?.id, 18843);
  assert.equal(report.closestLocalShape?.percentage, 100);
  assert.equal(report.remote.status, "not_run");
});

test("a built-in common setup fails before any API lookup and ignores its paths", async () => {
  const originalFetch = globalThis.fetch;
  let remoteCalls = 0;
  globalThis.fetch = async () => {
    remoteCalls += 1;
    throw new Error("The API should not be called for a built-in setup match.");
  };
  try {
    const report = await checkProblemDuplicates(
      commonSetup,
      parseSgf(commonSetup),
      { references: [] },
    );
    assert.equal(report.status, "fail");
    assert.equal(report.builtInSetupMatch?.id, "common-setup-001");
    assert.equal(report.remote.status, "not_run");
    assert.equal(remoteCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("built-in common setups accept every board symmetry and color reversal", () => {
  assertAllSetupVariants(
    "common-setup-001",
    [[0, 16], [1, 16], [2, 16], [3, 16], [4, 16], [4, 17], [4, 18]],
    [[0, 17], [1, 17], [2, 17], [3, 17], [3, 18]],
  );
  assertAllSetupVariants(
    "common-setup-002",
    [[15, 0], [15, 1], [15, 2], [15, 3], [16, 3], [16, 4], [17, 4], [18, 4]],
    [[16, 0], [16, 1], [16, 2], [17, 2], [17, 3], [18, 3]],
  );
});

test("the second built-in setup fails locally without inspecting its paths", async () => {
  const originalFetch = globalThis.fetch;
  let remoteCalls = 0;
  globalThis.fetch = async () => {
    remoteCalls += 1;
    throw new Error("The API should not be called for a built-in setup match.");
  };
  try {
    const report = await checkProblemDuplicates(
      commonSetupTwo,
      parseSgf(commonSetupTwo),
      { references: [] },
    );
    assert.equal(report.status, "fail");
    assert.equal(report.builtInSetupMatch?.id, "common-setup-002");
    assert.equal(report.remote.status, "not_run");
    assert.equal(remoteCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("built-in setup matching remains exact when a stone is added", async () => {
  const changed = commonSetup.replace("AB[aq]", "AB[ap][aq]");
  const report = await checkProblemDuplicates(
    changed,
    parseSgf(changed),
    { references: [] },
    { remote: false },
  );

  assert.equal(report.builtInSetupMatch, null);
});
