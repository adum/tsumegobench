import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { access, mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import type { DuplicateCorpus } from "../lib/duplicate-check";
import {
  checkOriginalityCandidate,
  quotaExceededResponse,
  type RemoteOriginalityLookup,
} from "../lib/originality-tool";

const emptyCorpus: DuplicateCorpus = { references: [] };
const clearRemote: RemoteOriginalityLookup = async () => ({
  cached: false,
  response: {
    radiusTwo: { signatures: [], entries: [], totalRecords: 0 },
    percentage: { topPercentage: 0, entries: [], totalRecords: 0 },
  },
});

async function withRun(
  callback: (runDir: string) => Promise<void>,
) {
  const runDir = await mkdtemp(path.join(os.tmpdir(), "tsumego-originality-"));
  try {
    await mkdir(path.join(runDir, "outputs"));
    await callback(runDir);
  } finally {
    await rm(runDir, { recursive: true, force: true });
  }
}

async function waitForFile(file: string, timeoutMilliseconds = 10_000) {
  const deadline = Date.now() + timeoutMilliseconds;
  while (Date.now() < deadline) {
    try {
      await access(file);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
  }
  throw new Error(`Timed out waiting for ${file}`);
}

test("a candidate without RIGHT returns an error before remote lookup", async () => {
  await withRun(async (runDir) => {
    await writeFile(
      path.join(runDir, "outputs", "problem-01.sgf"),
      "(;FF[4]GM[1]SZ[19]AB[aa][ba]AW[ab](;B[bb]))",
      "utf8",
    );
    let remoteCalls = 0;
    const response = await checkOriginalityCandidate({
      runDir,
      candidatePath: "outputs/problem-01.sgf",
      requestId: "missing-right",
      queryNumber: 1,
      queriesRemaining: 49,
      corpus: emptyCorpus,
      remoteLookup: async (sgf) => {
        remoteCalls += 1;
        return clearRemote(sgf);
      },
    });

    assert.equal(response.status, "invalid");
    assert.equal(response.queriesRemaining, 49);
    assert.ok(response.errors.some((error) => error.code === "missing-right"));
    assert.equal(remoteCalls, 0);
    assert.match(response.candidateSha256 ?? "", /^[a-f0-9]{64}$/);
  });
});

test("a built-in common setup is rejected without RIGHT before remote lookup", async () => {
  await withRun(async (runDir) => {
    await writeFile(
      path.join(runDir, "outputs", "problem-01.sgf"),
      "(;FF[4]GM[1]SZ[19]AB[aq][bq][cq][dq][eq][er][es]AW[ar][br][cr][dr][ds])",
      "utf8",
    );
    let remoteCalls = 0;
    const response = await checkOriginalityCandidate({
      runDir,
      candidatePath: "outputs/problem-01.sgf",
      requestId: "common-without-right",
      queryNumber: 1,
      queriesRemaining: 49,
      corpus: emptyCorpus,
      remoteLookup: async (sgf) => {
        remoteCalls += 1;
        return clearRemote(sgf);
      },
    });

    assert.equal(response.status, "duplicate");
    assert.equal(response.local?.builtInSetupMatch?.id, "common-setup-001");
    assert.equal(response.goProblems, null);
    assert.equal(remoteCalls, 0);
  });
});

test("same-run canonical duplicates are rejected", async () => {
  await withRun(async (runDir) => {
    const sgf = ";FF[4]GM[1]SZ[19]AB[aa][ba]AW[ab](;B[bb]C[RIGHT])";
    await writeFile(path.join(runDir, "outputs", "problem-01.sgf"), `(${sgf})`, "utf8");
    await writeFile(path.join(runDir, "outputs", "problem-02.sgf"), `(${sgf})`, "utf8");

    const response = await checkOriginalityCandidate({
      runDir,
      candidatePath: "outputs/problem-02.sgf",
      requestId: "peer-check",
      queryNumber: 2,
      queriesRemaining: 48,
      corpus: emptyCorpus,
      remoteLookup: clearRemote,
    });

    assert.equal(response.status, "duplicate");
    assert.deepEqual(response.local?.peerExactMatches, ["problem-01.sgf"]);
  });
});

test("a full-corpus percentage match can reject without a radius match", async () => {
  await withRun(async (runDir) => {
    await writeFile(
      path.join(runDir, "outputs", "problem-01.sgf"),
      "(;FF[4]GM[1]SZ[19]AB[aa][ba]AW[ab](;B[bb]C[RIGHT]))",
      "utf8",
    );
    const response = await checkOriginalityCandidate({
      runDir,
      candidatePath: "outputs/problem-01.sgf",
      requestId: "percentage-check",
      queryNumber: 3,
      queriesRemaining: 47,
      corpus: emptyCorpus,
      remoteLookup: async () => ({
        cached: false,
        response: {
          radiusTwo: { signatures: [], entries: [], totalRecords: 0 },
          percentage: {
            topPercentage: 92,
            entries: [
              {
                id: 59007,
                difficulty: "23 kyu?",
                createdAt: "2026-05-20",
                matchPercentage: 92,
              },
            ],
            totalRecords: 1,
          },
        },
      }),
    });

    assert.equal(response.status, "duplicate");
    assert.equal(response.goProblems?.signatureMatches.length, 0);
    assert.equal(response.goProblems?.topPercentage, 92);
    assert.equal(response.goProblems?.percentageMatches[0].id, 59007);
  });
});

test("quota errors do not claim to consume another query", () => {
  const response = quotaExceededResponse({
    requestId: "over-budget",
    candidatePath: "outputs/problem-01.sgf",
    queryLimit: 50,
  });
  assert.equal(response.status, "quota_exceeded");
  assert.equal(response.queryNumber, null);
  assert.equal(response.queriesRemaining, 0);
  assert.match(response.errors[0].message, /50/);
});

test("the broker enforces its query budget and records result totals", async () => {
  await withRun(async (runDir) => {
    await mkdir(path.join(runDir, "logs"));
    const auditDir = path.join(runDir, "test-private-audit");
    const child = spawn(
      process.execPath,
      [
        "--import",
        "tsx",
        "scripts/originality-broker.ts",
        "--run-dir",
        runDir,
        "--query-limit",
        "1",
        "--audit-dir",
        auditDir,
        "--poll-ms",
        "20",
      ],
      { cwd: process.cwd(), stdio: "ignore" },
    );
    try {
      await waitForFile(path.join(runDir, "originality", "ready.json"));
      await writeFile(
        path.join(runDir, "outputs", "problem-01.sgf"),
        "(;FF[4]GM[1]SZ[19]AB[aa][ba]AW[ab](;B[bb]))",
        "utf8",
      );
      await writeFile(
        path.join(runDir, "originality", "requests", "first.json"),
        JSON.stringify({ requestId: "first", path: "outputs/problem-01.sgf" }),
        "utf8",
      );
      await writeFile(
        path.join(runDir, "originality", "requests", "second.json"),
        JSON.stringify({ requestId: "second", path: "outputs/problem-01.sgf" }),
        "utf8",
      );
      const firstResult = path.join(runDir, "originality", "results", "first.json");
      const secondResult = path.join(runDir, "originality", "results", "second.json");
      await Promise.all([waitForFile(firstResult), waitForFile(secondResult)]);
      const first = JSON.parse(await readFile(firstResult, "utf8")) as {
        status: string;
        queriesRemaining: number;
      };
      const second = JSON.parse(await readFile(secondResult, "utf8")) as {
        status: string;
        queriesRemaining: number;
      };
      assert.equal(first.status, "invalid");
      assert.equal(first.queriesRemaining, 0);
      assert.equal(second.status, "quota_exceeded");
      assert.equal(second.queriesRemaining, 0);

      await writeFile(path.join(runDir, "originality", "stop"), "stop\n", "utf8");
      if (child.exitCode === null) {
        await new Promise<void>((resolve, reject) => {
          child.once("exit", (code) => (code === 0 ? resolve() : reject(new Error(`exit ${code}`))));
          child.once("error", reject);
        });
      } else {
        assert.equal(child.exitCode, 0);
      }
      const summary = JSON.parse(
        await readFile(path.join(runDir, "originality", "summary.json"), "utf8"),
      ) as {
        queryLimit: number;
        queriesUsed: number;
        quotaExceeded: number;
        results: { invalid: number };
      };
      assert.equal(summary.queryLimit, 1);
      assert.equal(summary.queriesUsed, 1);
      assert.equal(summary.quotaExceeded, 1);
      assert.equal(summary.results.invalid, 1);
    } finally {
      if (child.exitCode === null) child.kill();
    }
  });
});
