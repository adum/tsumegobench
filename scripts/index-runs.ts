import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

interface RunManifest {
  runId: string;
  status: string;
  createdAt: string;
  completedAt?: string | null;
  model: {
    provider: string;
    name: string;
    reasoningEffort?: string | null;
  };
  harness: {
    name: string;
    version?: string | null;
    exitCode?: number | null;
    durationSeconds?: number | null;
  };
  condition: Record<string, unknown>;
}

interface AutomatedEvaluation {
  status: string;
  evaluatedAt: string;
  configuration: Record<string, unknown>;
  summary: Record<string, number>;
  runChecks: unknown[];
  problems: Array<{
    file: string;
    targetDifficulty: string;
    playerColor: "black" | "white" | null;
    status: string;
    automatedGate: string;
    validation: unknown;
    originality: unknown;
    humanReviewRequired: string[];
  }>;
}

interface HumanEvaluation {
  updatedAt: string | null;
  reviewer: string | null;
  reviewerRank: string | null;
  problems: Array<Record<string, unknown> & { file: string }>;
}

async function readJson<T>(file: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(file, "utf8")) as T;
  } catch {
    return null;
  }
}

const projectRoot = process.cwd();
const runsDir = path.join(projectRoot, "runs");
const outputFile = path.join(projectRoot, "app", "data", "runs.generated.json");
await mkdir(runsDir, { recursive: true });

const entries = await readdir(runsDir, { withFileTypes: true });
const indexedRuns = [];

for (const entry of entries.filter((item) => item.isDirectory())) {
  const runDir = path.join(runsDir, entry.name);
  const manifest = await readJson<RunManifest>(path.join(runDir, "run.json"));
  const automated = await readJson<AutomatedEvaluation>(
    path.join(runDir, "evaluation", "automated.json"),
  );
  if (!manifest || !automated) continue;
  const human = await readJson<HumanEvaluation>(path.join(runDir, "evaluation", "human.json"));

  const problems = [];
  for (const problem of automated.problems) {
    let sgf: string | null = null;
    try {
      sgf = await readFile(path.join(runDir, "outputs", problem.file), "utf8");
    } catch {
      // Invalid or missing output remains browsable through its structured issues.
    }
    problems.push({
      ...problem,
      sgf,
      human: human?.problems.find((record) => record.file === problem.file) ?? null,
    });
  }

  indexedRuns.push({
    runId: manifest.runId,
    status: automated.status,
    createdAt: manifest.createdAt,
    completedAt: manifest.completedAt ?? null,
    model: manifest.model,
    harness: {
      name: manifest.harness.name,
      version: manifest.harness.version ?? null,
      exitCode: manifest.harness.exitCode ?? null,
      durationSeconds: manifest.harness.durationSeconds ?? null,
    },
    condition: manifest.condition,
    evaluatedAt: automated.evaluatedAt,
    configuration: automated.configuration,
    summary: automated.summary,
    runChecks: automated.runChecks,
    human: human
      ? {
          updatedAt: human.updatedAt,
          reviewer: human.reviewer,
          reviewerRank: human.reviewerRank,
        }
      : null,
    problems,
  });
}

indexedRuns.sort((left, right) => right.createdAt.localeCompare(left.createdAt));
await writeFile(outputFile, `${JSON.stringify(indexedRuns, null, 2)}\n`, "utf8");
process.stdout.write(`Indexed ${indexedRuns.length} benchmark run(s).\n`);
