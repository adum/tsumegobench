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
  assert.match(html, /Can a model invent a Go problem/);
  assert.match(html, /Reference problem lab|Reference laboratory/);
  assert.match(html, /Black to play|White to play/);
  assert.doesNotMatch(html, /Find the best (?:local )?result/i);
  assert.match(html, /One prompt\. Four gates\./);
  assert.match(html, /goproblems/i);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});
