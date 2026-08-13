import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { compactModelName, runHasSgfFiles } from "../app/components/RunBrowser";

test("slash-delimited model IDs display only their final fragment", () => {
  assert.equal(
    compactModelName("openrouter/deepseek/deepseek-v4-flash-0731"),
    "deepseek-v4-flash-0731",
  );
  assert.equal(compactModelName("gpt-5.6-luna"), "gpt-5.6-luna");
});

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

test("the server route provides one run-data snapshot to the client browser", async () => {
  const [runBrowserSource, runsPageSource] = await Promise.all([
    readFile(new URL("../app/components/RunBrowser.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/runs/page.tsx", import.meta.url), "utf8"),
  ]);

  assert.doesNotMatch(runBrowserSource, /runs\.generated\.json/);
  assert.match(runsPageSource, /runs\.generated\.json/);
  assert.match(runsPageSource, /<RunBrowser runs=/);
});
