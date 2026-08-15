import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const indexedRuns = JSON.parse(
  await readFile(new URL("../app/data/runs.generated.json", import.meta.url), "utf8"),
);
const modelMetadata = JSON.parse(
  await readFile(new URL("../data/model-metadata.json", import.meta.url), "utf8"),
);
const modelScores = JSON.parse(
  await readFile(new URL("../app/data/model-scores.generated.json", import.meta.url), "utf8"),
);
const canonicalModelIds = new Map(
  modelMetadata.models.flatMap((model) =>
    model.aliases.map((alias) => [`${alias.provider}/${alias.name}`, model.id]),
  ),
);
const evaluatedModelCount = new Set(
  indexedRuns.map((run) =>
    canonicalModelIds.get(`${run.model.provider}/${run.model.name}`) ??
      `${run.model.provider}/${run.model.name}`,
  ),
).size;
const unmatchedModelCount = new Set(
  indexedRuns
    .filter((run) => !canonicalModelIds.has(`${run.model.provider}/${run.model.name}`))
    .map((run) => `${run.model.provider}/${run.model.name}`),
).size;

function indexedRunReviewState(run) {
  const required = run.summary.humanReviewPending;
  const completed = Math.max(
    0,
    ...(run.humanReviews?.reviewers.map((reviewer) => reviewer.completed) ?? []),
  );
  const remaining = Math.max(0, required - completed);
  const status = run.status === "needs_human_review" && required > 0 && remaining === 0
    ? "reviewed"
    : run.status;
  return { remaining, status };
}

const defaultIndexedRun = indexedRuns.find((run) =>
  run.problems.some((problem) => problem.validation.valid && problem.sgf)
) ?? indexedRuns[0];
const selectedRunReviewState = indexedRunReviewState(defaultIndexedRun);
const latestIndexedRun = [...indexedRuns]
  .sort((left, right) => right.createdAt.localeCompare(left.createdAt))[0];
const latestIndexedRunStatus = indexedRunReviewState(latestIndexedRun).status;

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
  assert.match(html, /href="\/problems">Example Problems<\/a>/);
  assert.match(html, /href="\/runs"/);
  assert.match(html, /href="\/runs">Results<\/a>/);
  assert.match(html, /href="\/evaluation">Method<\/a>/);
  assert.match(html, /href="\/sources"/);
  assert.match(html, /<link[^>]+rel="icon"[^>]+href="\/favicon\.svg"/);
  assert.match(html, /19×19 boards/);
  assert.match(html, /Model summary/);
  assert.match(html, /Human score/);
  assert.match(html, /class="model-results-table"/);
  assert.match(html, /GPT-5\.6 Luna/);
  assert.match(html, /DeepSeek V4 Flash/);
  assert.match(html, /GLM-5\.2/);
  const modelSummary = html.match(
    /<table class="model-results-table">([\s\S]*?)<\/table>/,
  );
  assert.ok(modelSummary, "the model summary table should render");
  assert.match(
    modelSummary[1],
    /Claude Fable 5[\s\S]*?Anthropic[\s\S]*?low effort/,
  );
  assert.match(html, /src="\/provider-icons\/deepseek\.svg"/);
  assert.match(html, /src="\/provider-icons\/zai\.png"/);
  assert.match(html, /src="\/provider-icons\/(?:openai|anthropic|xai)\.svg"/);
  assert.match(html, /Score definition/);
  assert.match(html, /Latest benchmark activity/);
  assert.match(
    html,
    new RegExp(`class="run-log-status ${latestIndexedRunStatus}">${latestIndexedRunStatus}<\\/span>`),
  );
  assert.match(html, /Current finding/);
  assert.match(
    html,
    /models? (?:has|have) produced at least one problem that passed human review/,
  );
  assert.doesNotMatch(html, /human-passing result/);
  assert.match(html, /All LLMs By Release Date/);
  assert.match(html, /Score out of 10/);
  const topScorers = html.match(
    /<ol class="model-chart-legend" aria-label="Top scoring models">([\s\S]*?)<\/ol>/,
  );
  assert.ok(topScorers, "the top-scorer side table should render");
  assert.equal(
    (topScorers[1].match(/<li>/g) ?? []).length,
    Math.min(6, modelScores.models.filter((model) => model.score >= 1).length),
  );
  assert.match(
    html,
    new RegExp(`Models evaluated<\\/dt><dd>${evaluatedModelCount}<\\/dd>`),
  );
  if (unmatchedModelCount > 0) {
    assert.match(html, /Release metadata is still needed/);
  } else {
    assert.doesNotMatch(html, /Release metadata is still needed/);
  }
  assert.match(html, /class="model-chart-point"/);
  assert.match(html, /href="\/runs\?run=/);
  const statusIndex = html.indexOf('class="benchmark-status-grid"');
  const chartIndex = html.indexOf('class="home-model-chart"');
  const resultsIndex = html.indexOf('class="home-results-layout"');
  assert.ok(
    statusIndex >= 0 && statusIndex < chartIndex && chartIndex < resultsIndex,
    "the release-date graph should render immediately after the benchmark status strip",
  );
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
  assert.match(html, /class="run-provider-mark" aria-label="OpenAI model lab"/);
  assert.match(html, /src="\/provider-icons\/openai\.svg"/);
  assert.match(html, /class="run-effort">(?:default|low|high|max|xhigh) effort<\/span>/);
  const selectedStatusLabel = selectedRunReviewState.status.replaceAll("_", " ");
  assert.match(
    html,
    new RegExp(
      `class="run-badge ${selectedRunReviewState.status}">${selectedStatusLabel}<\\/span>`,
    ),
  );
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
  if (html.includes("Human review choices")) {
    assert.match(html, /Valid/);
    assert.match(html, /Realistic/);
    assert.match(html, /Duplicate/);
    assert.match(html, /Well pathed/);
  }
  assert.match(
    html,
    /class="run-pass-counts" aria-label="\d+ difficulty-credited, \d+ automated passed, \d+ total problems" title="Difficulty-credited \/ automated passed \/ total problems"/,
  );
  assert.match(
    html,
    /class="run-summary"[^>]*>[\s\S]*structural[\s\S]*original[\s\S]*to review[\s\S]*human score[\s\S]*<\/div>/,
  );
  assert.match(
    html,
    new RegExp(`<strong>${selectedRunReviewState.remaining}<\\/strong> to review`),
  );
  assert.match(html, /class="problem-thumbnail(?: is-empty)?"/);
  assert.match(html, /class="run-problem-tab-copy"/);
  assert.match(html, /class="sgf-source"[^>]*aria-label="SGF source for problem-\d{2}\.sgf"/);
  assert.match(html, />Copy SGF<\/button>/);
  assert.match(html, /<summary>Reveal SGF source<\/summary>/);
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
  assert.match(
    sources,
    /class="source-repository-link"[^>]+href="https:\/\/github\.com\/adum\/tsumegobench"[^>]+target="_blank"/,
  );
  assert.match(sources, /GitHub repository/);
  assert.match(sources, /adum\/tsumegobench/);
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
  assert.match(html, /property="og:image"[^>]+content="http:\/\/localhost(?::3000)?\/og\.png"/i);
  assert.match(html, /name="twitter:card"[^>]+content="summary_large_image"/i);
});
