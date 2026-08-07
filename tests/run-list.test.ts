import assert from "node:assert/strict";
import test from "node:test";
import { runHasSgfFiles } from "../app/components/RunBrowser";

test("run pass counts are hidden when no SGF files were found", () => {
  assert.equal(
    runHasSgfFiles({ summary: { filesFound: 0 }, problems: [{ sgf: null }] }),
    false,
  );
  assert.equal(
    runHasSgfFiles({ summary: { filesFound: 1 }, problems: [{ sgf: "(;SZ[19])" }] }),
    true,
  );
});

test("older indexes fall back to the embedded SGF contents", () => {
  assert.equal(
    runHasSgfFiles({ summary: {}, problems: [{ sgf: "" }, { sgf: null }] }),
    false,
  );
  assert.equal(
    runHasSgfFiles({ summary: {}, problems: [{ sgf: "(;SZ[19])" }] }),
    true,
  );
});
