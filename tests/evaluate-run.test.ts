import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

test("evaluator follows the ten outputs declared by a run manifest", async (context) => {
  const runDir = await mkdtemp(path.join(tmpdir(), "tsumego-bench-ten-"));
  context.after(() => rm(runDir, { recursive: true, force: true }));
  const outputs = Array.from(
    { length: 10 },
    (_, index) => `outputs/problem-${String(index + 1).padStart(2, "0")}.sgf`,
  );
  await writeFile(
    path.join(runDir, "run.json"),
    `${JSON.stringify({
      runId: "test-ten-problems",
      condition: { problemCount: 10 },
      artifacts: { outputs },
    })}\n`,
    "utf8",
  );

  execFileSync(
    process.execPath,
    [
      "--import",
      "tsx",
      "scripts/evaluate-run.ts",
      "--run-dir",
      runDir,
      "--local-only",
    ],
    { cwd: process.cwd(), stdio: "pipe" },
  );

  const automated = JSON.parse(
    await readFile(path.join(runDir, "evaluation", "automated.json"), "utf8"),
  );
  const human = JSON.parse(
    await readFile(path.join(runDir, "evaluation", "human.json"), "utf8"),
  );
  const reviews = JSON.parse(
    await readFile(path.join(runDir, "evaluation", "reviews.json"), "utf8"),
  );

  assert.equal(automated.summary.expectedProblems, 10);
  assert.equal(automated.problems.length, 10);
  assert.equal(automated.problems.at(-1).file, "problem-10.sgf");
  assert.deepEqual(
    automated.problems.map((problem: { targetDifficulty: string }) => problem.targetDifficulty),
    [
      "20–30 kyu",
      "20–30 kyu",
      "10–19 kyu",
      "10–19 kyu",
      "5–9 kyu",
      "5–9 kyu",
      "1–4 kyu",
      "1–4 kyu",
      "about 1 dan",
      "about 1 dan",
    ],
  );
  assert.equal(human.problems.length, 10);
  assert.equal(reviews.runId, "test-ten-problems");
  assert.deepEqual(reviews.reviews, []);
});

test("evaluator records a built-in setup duplicate even when RIGHT is missing", async (context) => {
  const runDir = await mkdtemp(path.join(tmpdir(), "tsumego-bench-common-"));
  context.after(() => rm(runDir, { recursive: true, force: true }));
  await mkdir(path.join(runDir, "outputs"));
  await writeFile(
    path.join(runDir, "run.json"),
    `${JSON.stringify({
      runId: "test-common-setup",
      condition: { problemCount: 1 },
      artifacts: { outputs: ["outputs/problem-01.sgf"] },
    })}\n`,
    "utf8",
  );
  await writeFile(
    path.join(runDir, "outputs", "problem-01.sgf"),
    "(;FF[4]GM[1]SZ[19]AB[aq][bq][cq][dq][eq][er][es]AW[ar][br][cr][dr][ds])",
    "utf8",
  );

  execFileSync(
    process.execPath,
    [
      "--import",
      "tsx",
      "scripts/evaluate-run.ts",
      "--run-dir",
      runDir,
      "--local-only",
    ],
    { cwd: process.cwd(), stdio: "pipe" },
  );

  const automated = JSON.parse(
    await readFile(path.join(runDir, "evaluation", "automated.json"), "utf8"),
  );
  const problem = automated.problems[0];
  assert.equal(problem.validation.valid, false);
  assert.ok(problem.validation.issues.some((issue: { code: string }) => issue.code === "missing-right"));
  assert.equal(problem.originality.status, "fail");
  assert.equal(problem.originality.builtInSetupMatch.id, "common-setup-001");
  assert.equal(problem.originality.remote.status, "not_run");
});
