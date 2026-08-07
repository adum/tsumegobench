import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { access, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  checkProblemDuplicates,
  loadDuplicateCorpus,
  type DuplicateReport,
} from "../lib/duplicate-check";
import { findBuiltInSetupDuplicate } from "../lib/common-setup-duplicates";
import {
  canonicalProblemFingerprint,
  canonicalRightShapes,
  getMove,
  shapeSimilarity,
  type SgfNode,
} from "../lib/sgf";
import { validateSgf, type ValidationIssue } from "../lib/validate-sgf";

type CheckStatus = "pass" | "fail" | "warning" | "not_run" | "needs_human_review";

interface CheckResult {
  id: string;
  status: CheckStatus;
  message: string;
}

interface RunManifest {
  runId?: string;
  benchmark?: {
    inputFiles?: Array<{ path: string; sha256: string }>;
  };
  condition?: {
    problemCount?: number;
    duplicateToolEnabled?: boolean;
  };
  artifacts?: {
    outputs?: string[];
  };
}

interface OriginalityToolResponse {
  path: string | null;
  status: string;
  candidateSha256: string | null;
}

interface ProblemEvaluation {
  file: string;
  targetDifficulty: string;
  sha256: string | null;
  playerColor: "black" | "white" | null;
  status: "failed" | "incomplete" | "needs_human_review";
  automatedGate: "pass" | "fail" | "incomplete";
  validation: {
    status: "pass" | "fail";
    valid: boolean;
    issues: ValidationIssue[];
    stats: ReturnType<typeof validateSgf>["stats"] | null;
  };
  originality: DuplicateReport & {
    peerExactMatches: string[];
    peerShapeMatches: Array<{ file: string; percentage: number }>;
  };
  humanReviewRequired: string[];
  _root?: SgfNode;
  _fingerprint?: string;
  _rightShapes?: string[];
}

const LEGACY_EXPECTED_PROBLEMS = [
  ["problem-01.sgf", "20–30 kyu"],
  ["problem-02.sgf", "10–19 kyu"],
  ["problem-03.sgf", "5–9 kyu"],
  ["problem-04.sgf", "1–4 kyu"],
  ["problem-05.sgf", "about 1 dan"],
] as const;

const DIFFICULTY_BANDS = LEGACY_EXPECTED_PROBLEMS.map(([, difficulty]) => difficulty);

function problemFileNames(count: number) {
  return Array.from(
    { length: count },
    (_, index) => `problem-${String(index + 1).padStart(2, "0")}.sgf`,
  );
}

function targetDifficulty(index: number, count: number) {
  const bandIndex = Math.min(
    DIFFICULTY_BANDS.length - 1,
    Math.floor((index * DIFFICULTY_BANDS.length) / count),
  );
  return DIFFICULTY_BANDS[bandIndex];
}

function expectedProblemNames(manifest: RunManifest) {
  const declared = manifest.artifacts?.outputs;
  if (declared?.length) return declared.map((file) => path.basename(file));
  const configuredCount = manifest.condition?.problemCount;
  const count =
    typeof configuredCount === "number" &&
    Number.isInteger(configuredCount) &&
    configuredCount > 0
      ? configuredCount
      : LEGACY_EXPECTED_PROBLEMS.length;
  return problemFileNames(count);
}

function getArgument(name: string) {
  const inline = process.argv.find((argument) => argument.startsWith(`${name}=`));
  if (inline) return inline.slice(name.length + 1);
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function sha256(content: string | Buffer) {
  return createHash("sha256").update(content).digest("hex");
}

async function pathExists(target: string) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

function gitCommit() {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], {
      cwd: process.cwd(),
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return null;
  }
}

const runArgument = getArgument("--run-dir");
if (!runArgument) {
  process.stderr.write(
    "Usage: npm run evaluate:run -- --run-dir runs/<run-id> [--local-only]\n",
  );
  process.exit(2);
}

const runDir = path.resolve(runArgument);
const outputsDir = path.join(runDir, "outputs");
const evaluationDir = path.join(runDir, "evaluation");
const localOnly = process.argv.includes("--local-only");
const threshold = Number.parseInt(getArgument("--threshold") ?? "90", 10);
const manualReviewThreshold = Number.parseInt(
  getArgument("--manual-review-threshold") ?? "80",
  10,
);

await mkdir(outputsDir, { recursive: true });
await mkdir(evaluationDir, { recursive: true });

let runManifest: RunManifest = {};
try {
  runManifest = JSON.parse(await readFile(path.join(runDir, "run.json"), "utf8")) as RunManifest;
} catch {
  // A standalone evaluation can still produce a useful record without run metadata.
}

const runId = runManifest.runId ?? path.basename(runDir);
const runChecks: CheckResult[] = [];
const outputEntries = await readdir(outputsDir, { withFileTypes: true });
const outputFiles = outputEntries.filter((entry) => entry.isFile()).map((entry) => entry.name).sort();
const expectedNames = expectedProblemNames(runManifest);
const expectedProblems = expectedNames.map(
  (file, index) => [file, targetDifficulty(index, expectedNames.length)] as const,
);
const missingNames = expectedNames.filter((file) => !outputFiles.includes(file));
const unexpectedNames = outputEntries
  .filter(
    (entry) => !entry.isFile() || !expectedNames.some((expectedName) => expectedName === entry.name),
  )
  .map((entry) => entry.name)
  .sort();

const originalityToolResponses: OriginalityToolResponse[] = [];
try {
  const audit = await readFile(path.join(runDir, "logs", "originality-tool.jsonl"), "utf8");
  for (const line of audit.split(/\r?\n/).filter(Boolean)) {
    originalityToolResponses.push(JSON.parse(line) as OriginalityToolResponse);
  }
} catch {
  // A disabled or failed tool has no trusted audit; the run check below records that state.
}

runChecks.push({
  id: "expected-files",
  status: missingNames.length ? "fail" : "pass",
  message: missingNames.length
    ? `Missing ${missingNames.join(", ")}.`
    : `All ${expectedNames.length} expected SGF files are present.`,
});
runChecks.push({
  id: "unexpected-files",
  status: unexpectedNames.length ? "fail" : "pass",
  message: unexpectedNames.length
    ? `Unexpected output files: ${unexpectedNames.join(", ")}.`
    : `The output directory contains only the ${expectedNames.length} expected files.`,
});

const changedInputs: string[] = [];
const inputFiles = runManifest.benchmark?.inputFiles ?? [];
for (const input of inputFiles) {
  const absolute = path.join(runDir, ...input.path.split("/"));
  try {
    if (sha256(await readFile(absolute)) !== input.sha256) changedInputs.push(input.path);
  } catch {
    changedInputs.push(input.path);
  }
}
runChecks.push({
  id: "input-integrity",
  status: !inputFiles.length ? "not_run" : changedInputs.length ? "fail" : "pass",
  message: !inputFiles.length
    ? "No input hash manifest was available for this standalone evaluation."
    : changedInputs.length
      ? `The model-visible input snapshot changed: ${changedInputs.join(", ")}.`
      : "The model-visible input snapshot is unchanged.",
});

const corpus = await loadDuplicateCorpus();
const problems: ProblemEvaluation[] = [];

for (let index = 0; index < expectedProblems.length; index += 1) {
  const [file, targetDifficulty] = expectedProblems[index];
  const absolute = path.join(outputsDir, file);
  let sgf: string | null = null;
  try {
    sgf = await readFile(absolute, "utf8");
  } catch {
    // Missing output is represented as a structural failure below.
  }

  const validation = sgf
    ? validateSgf(sgf)
    : {
        valid: false,
        issues: [
          {
            severity: "error" as const,
            code: "missing-file",
            message: `${file} was not created.`,
          },
        ],
      };
  const root = validation.root;
  const builtInSetupMatch = root ? findBuiltInSetupDuplicate(root) : null;
  const firstMove = root?.children.map(getMove).find(Boolean);
  const playerColor =
    firstMove?.color === "B" ? "black" : firstMove?.color === "W" ? "white" : null;

  let originality: ProblemEvaluation["originality"] = {
    status: "not_run",
    builtInSetupMatch: null,
    exactLocalMatch: null,
    closestLocalShape: null,
    remote: {
      status: "not_run",
      radiusTwoMatches: [],
      topPercentage: null,
      topMatchId: null,
      error: null,
    },
    peerExactMatches: [],
    peerShapeMatches: [],
  };
  if (sgf && root && (validation.valid || builtInSetupMatch)) {
    originality = {
      ...(await checkProblemDuplicates(sgf, root, corpus, {
        remote: !localOnly,
        failThreshold: threshold,
        manualReviewThreshold,
      })),
      peerExactMatches: [],
      peerShapeMatches: [],
    };
  }

  problems.push({
    file,
    targetDifficulty,
    sha256: sgf ? sha256(sgf) : null,
    playerColor,
    status: validation.valid ? "needs_human_review" : "failed",
    automatedGate: validation.valid ? "incomplete" : "fail",
    validation: {
      status: validation.valid ? "pass" : "fail",
      valid: validation.valid,
      issues: validation.issues,
      stats: validation.stats ?? null,
    },
    originality,
    humanReviewRequired: [
      "life-and-death correctness under best resistance",
      "complete solution and refutation coverage",
      "natural branch endpoints",
      "canonical construction and teaching value",
      `difficulty fit for ${targetDifficulty}`,
    ],
    _root: root,
    _fingerprint: root ? canonicalProblemFingerprint(root) : undefined,
    _rightShapes: root ? canonicalRightShapes(root) : undefined,
  });

  if (!localOnly && index < expectedProblems.length - 1) {
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
}

for (let leftIndex = 0; leftIndex < problems.length; leftIndex += 1) {
  const left = problems[leftIndex];
  if (!left._fingerprint || !left._rightShapes) continue;
  for (let rightIndex = leftIndex + 1; rightIndex < problems.length; rightIndex += 1) {
    const right = problems[rightIndex];
    if (!right._fingerprint || !right._rightShapes) continue;
    if (left._fingerprint === right._fingerprint) {
      left.originality.peerExactMatches.push(right.file);
      right.originality.peerExactMatches.push(left.file);
      continue;
    }
    const score = Math.max(
      0,
      ...left._rightShapes.flatMap((leftShape) =>
        right._rightShapes!.map((rightShape) => shapeSimilarity(leftShape, rightShape)),
      ),
    );
    const percentage = Math.round(score * 10_000) / 100;
    if (percentage >= manualReviewThreshold) {
      left.originality.peerShapeMatches.push({ file: right.file, percentage });
      right.originality.peerShapeMatches.push({ file: left.file, percentage });
    }
  }
}

for (const problem of problems) {
  const peerFailure = problem.originality.peerExactMatches.length > 0;
  const peerManualReview = problem.originality.peerShapeMatches.length > 0;
  if (!problem.validation.valid || problem.originality.status === "fail" || peerFailure) {
    problem.status = "failed";
    problem.automatedGate = "fail";
  } else if (problem.originality.status === "not_run") {
    problem.status = "incomplete";
    problem.automatedGate = "incomplete";
  } else {
    problem.status = "needs_human_review";
    problem.automatedGate = "pass";
  }
  if (peerManualReview && problem.status !== "failed") {
    problem.status = "needs_human_review";
  }
}

const colors = problems.map((problem) => problem.playerColor).filter(Boolean);
const blackCount = colors.filter((color) => color === "black").length;
const whiteCount = colors.filter((color) => color === "white").length;
runChecks.push({
  id: "player-color-range",
  status: blackCount >= 2 && whiteCount >= 2 ? "pass" : "fail",
  message:
    blackCount >= 2 && whiteCount >= 2
      ? `The set includes ${blackCount} Black-to-play and ${whiteCount} White-to-play problems.`
      : `The set requires at least two of each first-player color; found ${blackCount} Black and ${whiteCount} White.`,
});
runChecks.push({
  id: "difficulty-range",
  status: "needs_human_review",
  message:
    `The ${expectedProblems.length} per-file difficulty targets span the benchmark range; a human reviewer must verify the actual difficulty.`,
});

const duplicateToolEnabled = runManifest.condition?.duplicateToolEnabled === true;
const outputsWithoutFinalClear = problems
  .filter((problem) => {
    if (!problem.sha256) return true;
    const expectedPath = `outputs/${problem.file}`;
    return !originalityToolResponses.some(
      (response) =>
        response.status === "clear" &&
        response.path === expectedPath &&
        response.candidateSha256 === problem.sha256,
    );
  })
  .map((problem) => problem.file);
if (duplicateToolEnabled) {
  for (const problem of problems) {
    if (!outputsWithoutFinalClear.includes(problem.file)) continue;
    problem.status = "failed";
    problem.automatedGate = "fail";
  }
}
runChecks.push({
  id: "originality-tool-final-coverage",
  status: !duplicateToolEnabled
    ? "not_run"
    : outputsWithoutFinalClear.length
      ? "fail"
      : "pass",
  message: !duplicateToolEnabled
    ? "The live originality tool was disabled for this diagnostic run."
    : outputsWithoutFinalClear.length
      ? `No final clear originality result matched the exact output hash for: ${outputsWithoutFinalClear.join(", ")}.`
      : `All ${problems.length} exact final output hashes received a clear originality result.`,
});

const serializableProblems = problems.map((problem) => {
  const serializable = { ...problem };
  delete serializable._root;
  delete serializable._fingerprint;
  delete serializable._rightShapes;
  return serializable;
});
const failedProblems = serializableProblems.filter((problem) => problem.status === "failed").length;
const incompleteProblems = serializableProblems.filter(
  (problem) => problem.status === "incomplete",
).length;
const failedRunChecks = runChecks.filter((check) => check.status === "fail").length;
const automated = {
  $schema: "../../../schemas/automated-evaluation.schema.json",
  schemaVersion: 1,
  runId,
  evaluatedAt: new Date().toISOString(),
  evaluator: {
    commitSha: gitCommit(),
  },
  configuration: {
    remoteDuplicateChecks: !localOnly,
    duplicateFailThreshold: threshold,
    manualReviewThreshold,
  },
  status:
    failedProblems || failedRunChecks
      ? "failed"
      : incompleteProblems
        ? "incomplete"
        : "needs_human_review",
  runChecks,
  summary: {
    expectedProblems: expectedProblems.length,
    filesFound: expectedNames.filter((file) => outputFiles.includes(file)).length,
    structuralPassed: serializableProblems.filter((problem) => problem.validation.valid).length,
    originalityPassed: serializableProblems.filter(
      (problem) => problem.originality.status === "pass" && !problem.originality.peerExactMatches.length,
    ).length,
    automatedGatePassed: serializableProblems.filter(
      (problem) => problem.automatedGate === "pass",
    ).length,
    failedProblems,
    incompleteProblems,
    humanReviewPending: serializableProblems.filter(
      (problem) => problem.status === "needs_human_review",
    ).length,
    failedRunChecks,
  },
  problems: serializableProblems,
};

await writeFile(
  path.join(evaluationDir, "automated.json"),
  `${JSON.stringify(automated, null, 2)}\n`,
  "utf8",
);

const humanPath = path.join(evaluationDir, "human.json");
if (!(await pathExists(humanPath))) {
  const human = {
    $schema: "../../../schemas/human-evaluation.schema.json",
    schemaVersion: 1,
    runId,
    updatedAt: null,
    reviewer: null,
    reviewerRank: null,
    problems: expectedProblems.map(([file, targetDifficulty]) => ({
      file,
      status: "pending",
      targetDifficulty,
      estimatedDifficulty: null,
      structuralGate: null,
      localDuplicateGate: null,
      remoteDuplicateGate: null,
      scores: {
        correctness: null,
        treeCompleteness: null,
        canonicalStyle: null,
        pedagogicalFit: null,
        originality: null,
        total: null,
      },
      notes: "",
    })),
  };
  await writeFile(humanPath, `${JSON.stringify(human, null, 2)}\n`, "utf8");
}

const reviewsPath = path.join(evaluationDir, "reviews.json");
if (!(await pathExists(reviewsPath))) {
  const reviews = {
    $schema: "../../../schemas/human-reviews.schema.json",
    schemaVersion: 1,
    runId,
    updatedAt: null,
    reviews: [],
  };
  await writeFile(reviewsPath, `${JSON.stringify(reviews, null, 2)}\n`, "utf8");
}

const humanEvaluation = JSON.parse(await readFile(humanPath, "utf8")) as {
  updatedAt: string | null;
  reviewer: string | null;
  reviewerRank: string | null;
  problems: Array<Record<string, unknown> & { file: string; status: string }>;
};
const reviewerRecords = JSON.parse(await readFile(reviewsPath, "utf8")) as {
  updatedAt: string | null;
  reviews: Array<{
    reviewId: string;
    reviewerName: string;
    updatedAt: string;
    problems: Array<Record<string, unknown> & { file: string; status: string }>;
  }>;
};
const results = {
  schemaVersion: 1,
  runId,
  generatedAt: new Date().toISOString(),
  status: automated.status,
  automatedSummary: automated.summary,
  automatedRunChecks: automated.runChecks,
  configuration: automated.configuration,
  humanReview: {
    updatedAt: humanEvaluation.updatedAt,
    reviewer: humanEvaluation.reviewer,
    reviewerRank: humanEvaluation.reviewerRank,
    pending: humanEvaluation.problems.filter((problem) => problem.status === "pending").length,
    accepted: humanEvaluation.problems.filter((problem) => problem.status === "accepted").length,
    rejected: humanEvaluation.problems.filter((problem) => problem.status === "rejected").length,
  },
  humanReviews: {
    updatedAt: reviewerRecords.updatedAt,
    reviewCount: reviewerRecords.reviews.length,
    completedProblemReviews: reviewerRecords.reviews.reduce(
      (total, review) =>
        total + review.problems.filter((problem) => problem.status === "completed").length,
      0,
    ),
    reviewers: reviewerRecords.reviews.map((review) => ({
      reviewId: review.reviewId,
      reviewerName: review.reviewerName,
      updatedAt: review.updatedAt,
      completed: review.problems.filter((problem) => problem.status === "completed").length,
      total: review.problems.length,
    })),
  },
  problems: serializableProblems.map((problem) => ({
    ...problem,
    human:
      humanEvaluation.problems.find((humanProblem) => humanProblem.file === problem.file) ?? null,
    reviews: reviewerRecords.reviews.flatMap((review) => {
      const record = review.problems.find(
        (reviewedProblem) =>
          reviewedProblem.file === problem.file && reviewedProblem.status === "completed",
      );
      return record
        ? [{ reviewId: review.reviewId, reviewerName: review.reviewerName, ...record }]
        : [];
    }),
  })),
};
await writeFile(
  path.join(evaluationDir, "results.json"),
  `${JSON.stringify(results, null, 2)}\n`,
  "utf8",
);

process.stdout.write(
  `${JSON.stringify({
    runId,
    status: automated.status,
    output: path.relative(process.cwd(), path.join(evaluationDir, "automated.json")),
    summary: automated.summary,
  })}\n`,
);
