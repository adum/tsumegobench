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
  assert.match(html, /19×19 boards/);
  assert.match(html, /solution and refutation coverage, endpoint judgment/);
  assert.match(html, /Black to play|White to play/);
  assert.match(html, /aria-label="Problem 18843, Black to play/);
  assert.match(html, /1 dan/);
  assert.doesNotMatch(html, /class="principle-strip"/);
  assert.doesNotMatch(html, /aria-label="Filter problems"|Search ID, rank, source/);
  const thirtyKyuIndex = html.indexOf('aria-label="Problem 53750, White to play, 30 kyu');
  const oneKyuIndex = html.indexOf('aria-label="Problem 721, Black to play, 1 kyu');
  const oneDanIndex = html.indexOf('aria-label="Problem 17778, Black to play, 1 dan');
  assert.ok(
    thirtyKyuIndex >= 0 && oneKyuIndex >= 0 && thirtyKyuIndex < oneKyuIndex,
    "easier kyu problems should render before harder kyu problems",
  );
  assert.ok(
    oneDanIndex >= 0 && oneKyuIndex < oneDanIndex,
    "1 dan problems should render after the kyu problems",
  );
  assert.doesNotMatch(html, /Find the best (?:local )?result/i);
  assert.match(html, /Leads to RIGHT/);
  assert.match(html, /aria-label="Board variation legend"/);
  assert.match(html, /aria-label="Board navigation controls"/);
  assert.match(
    html,
    /aria-label="Board navigation controls"[\s\S]*class="go-board-canvas"/,
  );
  assert.doesNotMatch(html, /class="move-controls"/);
  assert.ok(
    html.indexOf('class="move-inspector"') >= 0 &&
      html.indexOf('class="move-inspector"') < html.indexOf('class="go-board-canvas"'),
    "move status should render above the board",
  );
  assert.ok(
    html.indexOf('class="tree-summary"') >= 0 &&
      html.indexOf('class="tree-summary"') < html.indexOf('class="solution-tree-scroll"'),
    "problem statistics should render above the solution tree",
  );
  assert.match(html, /next variations, \d+ leading to RIGHT/);
  assert.match(html, /Click a colored marker to select that variation/);
  assert.match(html, /Available board variations/);
  assert.doesNotMatch(html, />COORDINATES</i);
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
