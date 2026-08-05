import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    {
      ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Tsumego Bench reviewer", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Tsumego Bench — AI Go Problem Creation<\/title>/i);
  assert.match(html, /AI Go Problem Creation Benchmark/);
  assert.match(html, /Problem viewer/);
  assert.match(html, /Evaluation protocol/);
  assert.match(html, /Black to play|White to play/);
  assert.match(html, /aria-label="Problem 18843, Black to play/);
  assert.doesNotMatch(html, /Find the best (?:local )?result/i);
  assert.match(html, /Leads to RIGHT/);
  assert.match(html, /aria-label="Board variation legend"/);
  assert.match(html, /next variations, \d+ leading to RIGHT/);
  assert.match(html, /tree-edge has-result/);
  assert.match(html, /tree-edge no-result/);
  assert.doesNotMatch(html, /tree-coordinate/);
  assert.doesNotMatch(html, /type="checkbox"/i);
  assert.match(html, /goproblems/i);
  assert.doesNotMatch(html, /property="og:image"/i);
  assert.doesNotMatch(
    html,
    /Can a model invent|worth solving|evidence-first|Reference laboratory|Read the position|One prompt\. Four gates|No quiet repairs|difficult creative claim|does not pretend/i,
  );
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});
