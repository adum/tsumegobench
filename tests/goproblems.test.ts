import assert from "node:assert/strict";
import test from "node:test";
import { findSimilarProblems } from "../lib/goproblems";

test("radius and percentage searches remain independent full-corpus requests", async () => {
  const originalFetch = globalThis.fetch;
  const bodies: Array<Record<string, unknown>> = [];
  globalThis.fetch = async (_input, init) => {
    bodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
    if (bodies.length === 1) {
      return new Response(
        JSON.stringify({ signatures: ["signature"], entries: [{ id: 123 }], totalRecords: 1 }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response(
      JSON.stringify({ topPercentage: 92, entries: [{ id: 456 }], totalRecords: 1 }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  try {
    await findSimilarProblems("(;SZ[19])", { limit: 5 });
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(bodies[0].radii, [2]);
  assert.equal("includedIds" in bodies[0], false);
  assert.equal("includedIds" in bodies[1], false);
  assert.equal(bodies[1].limit, 5);
});
