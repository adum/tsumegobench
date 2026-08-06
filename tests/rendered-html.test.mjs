import assert from "node:assert/strict";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${path}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    {
      ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
    },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

async function htmlFor(path) {
  const response = await render(path);
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  return response.text();
}

test("server-renders a compact overview with route navigation", async () => {
  const html = await htmlFor("/");
  assert.match(html, /AI Go Problem Creation Benchmark/);
  assert.match(html, /href="\/problems"/);
  assert.match(html, /href="\/problems">Reference<\/a>/);
  assert.match(html, /href="\/runs"/);
  assert.match(html, /href="\/evaluation">Process<\/a>/);
  assert.match(html, /href="\/sources"/);
  assert.match(html, /<link[^>]+rel="icon"[^>]+href="\/favicon\.svg"/);
  assert.match(html, /19×19 boards/);
  assert.doesNotMatch(html, /class="workbench-shell/);
  assert.doesNotMatch(html, /class="protocol-grid/);
});

test("server-renders reference problems on their own page", async () => {
  const html = await htmlFor("/problems");
  assert.match(html, /Problem viewer/);
  assert.doesNotMatch(html, /class="runs-section/);
  assert.doesNotMatch(html, /class="protocol-section/);
  assert.match(html, /aria-label="Problem 18843, Black to play/);
  assert.match(html, /1 dan/);
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
  assert.doesNotMatch(html, /CHOICE|FORCE|NOTTHIS/);
  assert.match(html, /Leads to RIGHT/);
  assert.match(html, /aria-label="Board variation legend"/);
  assert.match(html, /class="to-move-stone white"[^>]*aria-label="White to play"/);
  assert.match(
    html,
    /aria-label="White to play"[\s\S]*aria-label="Board navigation controls"[\s\S]*class="go-board-canvas"/,
  );
  assert.doesNotMatch(html, /<h3>White to play<\/h3>|<h3>Black to play<\/h3>/);
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
  assert.doesNotMatch(html, />COORDINATES</i);
  assert.match(html, /tree-edge has-result/);
  assert.match(html, /tree-edge no-result/);
  assert.doesNotMatch(html, /tree-coordinate/);
  assert.doesNotMatch(html, /type="checkbox"/i);
});

test("server-renders generated runs on their own page with a to-move stone", async () => {
  const html = await htmlFor("/runs");
  assert.match(html, /Benchmark runs/);
  assert.match(html, /gpt-5\.6-(?:luna|sol)/);
  assert.doesNotMatch(html, /Problem viewer/);
  const toMove = html.match(
    /class="to-move-stone (black|white)"[^>]*aria-label="(Black|White) to play"/,
  );
  assert.ok(toMove, "the selected generated problem should show its player-to-move stone");
  assert.equal(toMove[2].toLowerCase(), toMove[1]);
  assert.match(
    html,
    /aria-label="(?:Black|White) to play"[\s\S]*aria-label="Generated board navigation controls"[\s\S]*class="go-board-canvas"/,
  );
  assert.match(
    html,
    /href="https:\/\/www\.goproblems\.com\/problems\/\d+"[^>]*target="_blank"/,
  );
  assert.match(html, /Human review choices/);
  assert.match(html, /Valid/);
  assert.match(html, /Realistic/);
  assert.match(html, /Duplicate/);
  assert.match(html, /Well pathed/);
  assert.match(html, /adam/);
  assert.match(
    html,
    /class="run-pass-counts" aria-label="\d+ human passed, \d+ automated passed, \d+ total problems" title="Human passed \/ automated passed \/ total problems"/,
  );
  assert.match(
    html,
    /class="run-summary"[^>]*>[\s\S]*structural[\s\S]*original[\s\S]*to review[\s\S]*human passed[\s\S]*<\/div>/,
  );
});

test("server-renders process and sources as dedicated pages", async () => {
  const evaluation = await htmlFor("/evaluation");
  assert.match(evaluation, /Benchmark process/);
  assert.match(evaluation, /solution and refutation coverage, endpoint judgment/);
  assert.doesNotMatch(evaluation, /Problem viewer|Benchmark runs/);

  const sources = await htmlFor("/sources");
  assert.match(sources, /Guidance and APIs/);
  assert.match(sources, /Problem types/);
  assert.match(sources, /Solution signatures/);
  assert.match(sources, /github\.com\/adum\/tsumegobench/);
});

test("rendered pages omit retired controls and marketing copy", async () => {
  const pages = await Promise.all(["/", "/problems", "/runs", "/evaluation", "/sources"].map(htmlFor));
  const html = pages.join("\n");
  assert.doesNotMatch(html, /class="principle-strip"/);
  assert.doesNotMatch(html, /class="move-controls"/);
  assert.doesNotMatch(
    html,
    /Can a model invent|worth solving|evidence-first|Reference laboratory|Read the position|One prompt\. Four gates|No quiet repairs|difficult creative claim|does not pretend/i,
  );
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
  assert.doesNotMatch(html, /property="og:image"/i);
});
