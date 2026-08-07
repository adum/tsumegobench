import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { findBuiltInSetupDuplicate } from "./common-setup-duplicates";
import {
  checkProblemDuplicates,
  type DuplicateCorpus,
} from "./duplicate-check";
import {
  findSimilarProblems,
  type PercentageResponse,
  type SimilarResponse,
} from "./goproblems";
import {
  canonicalProblemFingerprint,
  canonicalRightShapes,
  shapeSimilarity,
} from "./sgf";
import { validateSgf, type ValidationIssue } from "./validate-sgf";

export const ORIGINALITY_FAIL_THRESHOLD = 90;
export const ORIGINALITY_REVIEW_THRESHOLD = 80;

export type OriginalityToolStatus =
  | "clear"
  | "review"
  | "duplicate"
  | "invalid"
  | "unavailable"
  | "quota_exceeded";

interface CompactProblemMatch {
  id: number;
  difficulty: string;
  createdAt: string;
  percentage?: number;
  url: string;
}

export interface OriginalityToolResponse {
  schemaVersion: 1;
  requestId: string;
  path: string | null;
  queryNumber: number | null;
  queriesRemaining: number;
  checkedAt: string;
  status: OriginalityToolStatus;
  candidateSha256: string | null;
  cachedRemote: boolean;
  local: {
    builtInSetupMatch: { id: string; label: string } | null;
    exactReferenceMatch: { id: number; url: string } | null;
    closestReferenceMatch: { id: number; percentage: number; url: string } | null;
    peerExactMatches: string[];
    peerShapeMatches: Array<{ file: string; percentage: number }>;
  } | null;
  goProblems: {
    radius: 2;
    signatureMatches: CompactProblemMatch[];
    topPercentage: number;
    percentageMatches: CompactProblemMatch[];
  } | null;
  errors: Array<{ code: string; message: string }>;
}

export interface RemoteLookupResult {
  response: {
    radiusTwo: SimilarResponse;
    percentage: PercentageResponse;
  };
  cached: boolean;
}

export type RemoteOriginalityLookup = (sgf: string) => Promise<RemoteLookupResult>;

function sha256(content: string) {
  return createHash("sha256").update(content).digest("hex");
}

function compactValidationErrors(issues: ValidationIssue[]) {
  return issues
    .filter((issue) => issue.severity === "error")
    .map(({ code, message }) => ({ code, message }));
}

function percentageBetween(first: string[], second: string[]) {
  const score = Math.max(
    0,
    ...first.flatMap((left) => second.map((right) => shapeSimilarity(left, right))),
  );
  return Math.round(score * 10_000) / 100;
}

function compactSignatureMatch(entry: SimilarResponse["entries"][number]): CompactProblemMatch {
  return {
    id: entry.id,
    difficulty: entry.difficulty,
    createdAt: entry.createdAt,
    url: `https://www.goproblems.com/problems/${entry.id}`,
  };
}

function compactPercentageMatch(
  entry: PercentageResponse["entries"][number],
): CompactProblemMatch {
  return {
    ...compactSignatureMatch(entry),
    percentage: entry.matchPercentage ?? 0,
  };
}

function invalidResponse(
  requestId: string,
  candidatePath: string | null,
  queryNumber: number,
  queriesRemaining: number,
  candidateSha256: string | null,
  errors: Array<{ code: string; message: string }>,
): OriginalityToolResponse {
  return {
    schemaVersion: 1,
    requestId,
    path: candidatePath,
    queryNumber,
    queriesRemaining,
    checkedAt: new Date().toISOString(),
    status: "invalid",
    candidateSha256,
    cachedRemote: false,
    local: null,
    goProblems: null,
    errors,
  };
}

export async function checkOriginalityCandidate(options: {
  runDir: string;
  candidatePath: string;
  requestId: string;
  queryNumber: number;
  queriesRemaining: number;
  corpus: DuplicateCorpus;
  remoteLookup?: RemoteOriginalityLookup;
  failThreshold?: number;
  reviewThreshold?: number;
}): Promise<OriginalityToolResponse> {
  const failThreshold = options.failThreshold ?? ORIGINALITY_FAIL_THRESHOLD;
  const reviewThreshold = options.reviewThreshold ?? ORIGINALITY_REVIEW_THRESHOLD;
  const normalizedPath = options.candidatePath.replaceAll("\\", "/");
  if (!/^outputs\/problem-[0-9]{2}\.sgf$/.test(normalizedPath)) {
    return invalidResponse(
      options.requestId,
      normalizedPath,
      options.queryNumber,
      options.queriesRemaining,
      null,
      [
      {
        code: "invalid-path",
        message: "The path must name an SGF as outputs/problem-NN.sgf.",
      },
      ],
    );
  }

  const outputsDir = path.resolve(options.runDir, "outputs");
  const absoluteCandidate = path.resolve(options.runDir, ...normalizedPath.split("/"));
  if (path.dirname(absoluteCandidate) !== outputsDir) {
    return invalidResponse(
      options.requestId,
      normalizedPath,
      options.queryNumber,
      options.queriesRemaining,
      null,
      [
        {
          code: "invalid-path",
          message: "The candidate must be inside the run output directory.",
        },
      ],
    );
  }

  let sgf: string;
  try {
    sgf = await readFile(absoluteCandidate, "utf8");
  } catch {
    return invalidResponse(
      options.requestId,
      normalizedPath,
      options.queryNumber,
      options.queriesRemaining,
      null,
      [{ code: "missing-file", message: `${normalizedPath} does not exist or cannot be read.` }],
    );
  }

  const candidateSha256 = sha256(sgf);
  const validation = validateSgf(sgf);
  const validationErrors = compactValidationErrors(validation.issues);
  const builtInSetupMatch = validation.root
    ? findBuiltInSetupDuplicate(validation.root)
    : null;
  if (builtInSetupMatch) {
    return {
      schemaVersion: 1,
      requestId: options.requestId,
      path: normalizedPath,
      queryNumber: options.queryNumber,
      queriesRemaining: options.queriesRemaining,
      checkedAt: new Date().toISOString(),
      status: "duplicate",
      candidateSha256,
      cachedRemote: false,
      local: {
        builtInSetupMatch,
        exactReferenceMatch: null,
        closestReferenceMatch: null,
        peerExactMatches: [],
        peerShapeMatches: [],
      },
      goProblems: null,
      errors: [],
    };
  }
  if (!validation.valid || !validation.root) {
    const missingRight = validationErrors.some((error) => error.code === "missing-right");
    return invalidResponse(
      options.requestId,
      normalizedPath,
      options.queryNumber,
      options.queriesRemaining,
      candidateSha256,
      missingRight
        ? [
            {
              code: "missing-right",
              message:
                "Duplicate checking requires at least one accepted solution path ending in C[RIGHT].",
            },
            ...validationErrors.filter((error) => error.code !== "missing-right"),
          ]
        : validationErrors,
    );
  }

  const localReport = await checkProblemDuplicates(
    sgf,
    validation.root,
    options.corpus,
    { remote: false, failThreshold, manualReviewThreshold: reviewThreshold },
  );
  const candidateFingerprint = canonicalProblemFingerprint(validation.root);
  const candidateShapes = canonicalRightShapes(validation.root);
  const peerExactMatches: string[] = [];
  const peerShapeMatches: Array<{ file: string; percentage: number }> = [];
  const outputEntries = await readdir(outputsDir, { withFileTypes: true });
  for (const entry of outputEntries) {
    if (!entry.isFile() || !entry.name.endsWith(".sgf") || entry.name === path.basename(normalizedPath)) {
      continue;
    }
    try {
      const peerSgf = await readFile(path.join(outputsDir, entry.name), "utf8");
      const peerValidation = validateSgf(peerSgf);
      if (!peerValidation.valid || !peerValidation.root) continue;
      if (canonicalProblemFingerprint(peerValidation.root) === candidateFingerprint) {
        peerExactMatches.push(entry.name);
        continue;
      }
      const percentage = percentageBetween(
        candidateShapes,
        canonicalRightShapes(peerValidation.root),
      );
      if (percentage >= reviewThreshold) {
        peerShapeMatches.push({ file: entry.name, percentage });
      }
    } catch {
      // An unreadable peer cannot make this candidate invalid; final evaluation reports it separately.
    }
  }

  const local = {
    builtInSetupMatch: localReport.builtInSetupMatch,
    exactReferenceMatch: localReport.exactLocalMatch
      ? {
          id: localReport.exactLocalMatch.id,
          url: localReport.exactLocalMatch.sourceUrl,
        }
      : null,
    closestReferenceMatch: localReport.closestLocalShape
      ? {
          id: localReport.closestLocalShape.id,
          percentage: localReport.closestLocalShape.percentage,
          url: localReport.closestLocalShape.sourceUrl,
        }
      : null,
    peerExactMatches: peerExactMatches.sort(),
    peerShapeMatches: peerShapeMatches.sort((left, right) => right.percentage - left.percentage),
  };

  const lookup =
    options.remoteLookup ??
    (async (candidate: string) => ({
      response: await findSimilarProblems(candidate),
      cached: false,
    }));
  try {
    const remote = await lookup(sgf);
    const signatureMatches = remote.response.radiusTwo.entries.map(compactSignatureMatch);
    const percentageMatches = remote.response.percentage.entries.map(compactPercentageMatch);
    const topPercentage = remote.response.percentage.topPercentage ?? 0;
    const goProblems = {
      radius: 2 as const,
      signatureMatches,
      topPercentage,
      percentageMatches,
    };
    const duplicate = Boolean(
      local.builtInSetupMatch ||
        local.exactReferenceMatch ||
        local.peerExactMatches.length ||
        signatureMatches.length ||
        topPercentage >= failThreshold,
    );
    const review = Boolean(
      (local.closestReferenceMatch?.percentage ?? 0) >= reviewThreshold ||
        local.peerShapeMatches.length ||
        topPercentage >= reviewThreshold,
    );
    return {
      schemaVersion: 1,
      requestId: options.requestId,
      path: normalizedPath,
      queryNumber: options.queryNumber,
      queriesRemaining: options.queriesRemaining,
      checkedAt: new Date().toISOString(),
      status: duplicate ? "duplicate" : review ? "review" : "clear",
      candidateSha256,
      cachedRemote: remote.cached,
      local,
      goProblems,
      errors: [],
    };
  } catch (error) {
    return {
      schemaVersion: 1,
      requestId: options.requestId,
      path: normalizedPath,
      queryNumber: options.queryNumber,
      queriesRemaining: options.queriesRemaining,
      checkedAt: new Date().toISOString(),
      status: "unavailable",
      candidateSha256,
      cachedRemote: false,
      local,
      goProblems: null,
      errors: [
        {
          code: "goproblems-unavailable",
          message: error instanceof Error ? error.message : "The GoProblems checks failed.",
        },
      ],
    };
  }
}

export function quotaExceededResponse(options: {
  requestId: string;
  candidatePath: string | null;
  queryLimit: number;
}): OriginalityToolResponse {
  return {
    schemaVersion: 1,
    requestId: options.requestId,
    path: options.candidatePath,
    queryNumber: null,
    queriesRemaining: 0,
    checkedAt: new Date().toISOString(),
    status: "quota_exceeded",
    candidateSha256: null,
    cachedRemote: false,
    local: null,
    goProblems: null,
    errors: [
      {
        code: "query-limit-exceeded",
        message: `The originality query budget of ${options.queryLimit} has been exhausted.`,
      },
    ],
  };
}
