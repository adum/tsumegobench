import { createHash } from "node:crypto";
import {
  access,
  appendFile,
  mkdir,
  readFile,
  readdir,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { loadDuplicateCorpus } from "../lib/duplicate-check";
import { findSimilarProblems } from "../lib/goproblems";
import {
  checkOriginalityCandidate,
  quotaExceededResponse,
  type OriginalityToolResponse,
  type OriginalityToolStatus,
} from "../lib/originality-tool";

function getArgument(name: string) {
  const inline = process.argv.find((argument) => argument.startsWith(`${name}=`));
  if (inline) return inline.slice(name.length + 1);
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function sha256(content: string) {
  return createHash("sha256").update(content).digest("hex");
}

async function exists(file: string) {
  try {
    await access(file);
    return true;
  } catch {
    return false;
  }
}

function sleep(milliseconds: number) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

const runArgument = getArgument("--run-dir");
const auditArgument = getArgument("--audit-dir");
const queryLimit = Number.parseInt(getArgument("--query-limit") ?? "0", 10);
const pollMilliseconds = Number.parseInt(getArgument("--poll-ms") ?? "200", 10);
if (!runArgument || !auditArgument || !Number.isInteger(queryLimit) || queryLimit < 1) {
  process.stderr.write(
    "Usage: originality-broker --run-dir <run> --audit-dir <private directory> --query-limit <positive integer>\n",
  );
  process.exit(2);
}

const projectRoot = process.cwd();
const runDir = path.resolve(runArgument);
const auditDir = path.resolve(auditArgument);
const originalityDir = path.join(runDir, "originality");
const requestsDir = path.join(originalityDir, "requests");
const resultsDir = path.join(originalityDir, "results");
const summaryFile = path.join(originalityDir, "summary.json");
const trustedSummaryFile = path.join(auditDir, "summary.json");
const readyFile = path.join(originalityDir, "ready.json");
const stopFile = path.join(originalityDir, "stop");
const auditFile = path.join(auditDir, "audit.jsonl");

await mkdir(requestsDir, { recursive: true });
await mkdir(resultsDir, { recursive: true });
await mkdir(auditDir, { recursive: true });
await writeFile(auditFile, "", "utf8");
const corpus = await loadDuplicateCorpus(projectRoot);
const resultCounts: Record<Exclude<OriginalityToolStatus, "quota_exceeded">, number> = {
  clear: 0,
  review: 0,
  duplicate: 0,
  invalid: 0,
  unavailable: 0,
};
let queriesUsed = 0;
let quotaExceeded = 0;
let remoteCacheHits = 0;
const remoteCache = new Map<
  string,
  Awaited<ReturnType<typeof findSimilarProblems>>
>();

function summary() {
  return {
    schemaVersion: 1,
    queryLimit,
    queriesUsed,
    queriesRemaining: Math.max(0, queryLimit - queriesUsed),
    quotaExceeded,
    remoteCacheHits,
    results: resultCounts,
    updatedAt: new Date().toISOString(),
  };
}

async function writeSummary() {
  const contents = `${JSON.stringify(summary(), null, 2)}\n`;
  await writeFile(summaryFile, contents, "utf8");
  await writeFile(trustedSummaryFile, contents, "utf8");
}

async function recordResult(resultFile: string, result: OriginalityToolResponse) {
  await writeFile(resultFile, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  await appendFile(auditFile, `${JSON.stringify(result)}\n`, "utf8");
  if (result.status === "quota_exceeded") quotaExceeded += 1;
  else resultCounts[result.status] += 1;
  if (result.cachedRemote) remoteCacheHits += 1;
  await writeSummary();
}

function invalidRequest(options: {
  requestId: string;
  candidatePath: string | null;
  queryNumber: number;
  queriesRemaining: number;
  code: string;
  message: string;
}): OriginalityToolResponse {
  return {
    schemaVersion: 1,
    requestId: options.requestId,
    path: options.candidatePath,
    queryNumber: options.queryNumber,
    queriesRemaining: options.queriesRemaining,
    checkedAt: new Date().toISOString(),
    status: "invalid",
    candidateSha256: null,
    cachedRemote: false,
    local: null,
    goProblems: null,
    errors: [{ code: options.code, message: options.message }],
  };
}

await writeSummary();
await writeFile(
  readyFile,
  `${JSON.stringify(
    {
      schemaVersion: 1,
      status: "ready",
      queryLimit,
      startedAt: new Date().toISOString(),
    },
    null,
    2,
  )}\n`,
  "utf8",
);
process.stdout.write(`Originality broker ready with ${queryLimit} queries.\n`);

const observations = new Map<string, string>();
const processedVersions = new Map<string, string>();
let stopping = false;

while (true) {
  const requestFiles = (await readdir(requestsDir, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => entry.name)
    .sort();
  let waitingForStableFile = false;

  for (const filename of requestFiles) {
    const requestFile = path.join(requestsDir, filename);
    let raw: string;
    try {
      raw = await readFile(requestFile, "utf8");
    } catch {
      continue;
    }
    const version = sha256(raw);
    if (processedVersions.get(filename) === version) continue;
    if (observations.get(filename) !== version) {
      observations.set(filename, version);
      waitingForStableFile = true;
      continue;
    }

    processedVersions.set(filename, version);
    const fileRequestId = filename.slice(0, -".json".length);
    const resultFile = path.join(resultsDir, filename);
    let request: { requestId?: unknown; path?: unknown } = {};
    try {
      request = JSON.parse(raw) as { requestId?: unknown; path?: unknown };
    } catch {
      // The stable malformed request is recorded below.
    }
    const requestId = typeof request.requestId === "string" ? request.requestId : fileRequestId;
    const candidatePath = typeof request.path === "string" ? request.path : null;

    if (queriesUsed >= queryLimit) {
      await recordResult(
        resultFile,
        quotaExceededResponse({ requestId, candidatePath, queryLimit }),
      );
      continue;
    }

    queriesUsed += 1;
    const queryNumber = queriesUsed;
    const queriesRemaining = Math.max(0, queryLimit - queriesUsed);
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(fileRequestId)) {
      await recordResult(
        resultFile,
        invalidRequest({
          requestId,
          candidatePath,
          queryNumber,
          queriesRemaining,
          code: "invalid-request-id",
          message: "The request filename must contain only letters, numbers, dots, dashes, or underscores.",
        }),
      );
      continue;
    }
    if (requestId !== fileRequestId) {
      await recordResult(
        resultFile,
        invalidRequest({
          requestId,
          candidatePath,
          queryNumber,
          queriesRemaining,
          code: "request-id-mismatch",
          message: "requestId must equal the request filename without .json.",
        }),
      );
      continue;
    }
    if (!candidatePath) {
      await recordResult(
        resultFile,
        invalidRequest({
          requestId,
          candidatePath,
          queryNumber,
          queriesRemaining,
          code: "missing-path",
          message: "The request must include path: outputs/problem-NN.sgf.",
        }),
      );
      continue;
    }

    const result = await checkOriginalityCandidate({
      runDir,
      candidatePath,
      requestId,
      queryNumber,
      queriesRemaining,
      corpus,
      remoteLookup: async (sgf) => {
        const hash = sha256(sgf);
        const cached = remoteCache.get(hash);
        if (cached) return { response: cached, cached: true };
        const response = await findSimilarProblems(sgf);
        remoteCache.set(hash, response);
        return { response, cached: false };
      },
    });
    await recordResult(resultFile, result);
  }

  stopping = stopping || (await exists(stopFile));
  if (stopping && !waitingForStableFile) break;
  await sleep(pollMilliseconds);
}

await writeSummary();
process.stdout.write(
  `Originality broker stopped after ${queriesUsed}/${queryLimit} queries.\n`,
);
