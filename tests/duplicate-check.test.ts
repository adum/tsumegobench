import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { checkProblemDuplicates, loadDuplicateCorpus } from "../lib/duplicate-check";
import { parseSgf } from "../lib/sgf";

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
