import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  canonicalProblemFingerprint,
  canonicalRightShapes,
  parseSgf,
  shapeSimilarity,
} from "../lib/sgf";
import { findSimilarProblems } from "../lib/goproblems";
import { validateSgf } from "../lib/validate-sgf";

interface ManifestRecord {
  id: number;
  sgfFile: string;
  sourceUrl: string;
}

interface Manifest {
  problems: ManifestRecord[];
}

const argumentsList = process.argv.slice(2);
const fileArgument = argumentsList.find((argument) => !argument.startsWith("--"));
if (!fileArgument) {
  process.stderr.write(
    "Usage: npm run duplicates -- submissions/run-name/problem.sgf [--local-only] [--threshold=90] [--exclude-id=123]\n",
  );
  process.exit(2);
}

const thresholdArgument = argumentsList.find((argument) => argument.startsWith("--threshold="));
const threshold = Number.parseInt(thresholdArgument?.split("=")[1] ?? "90", 10);
const excludedIdArgument = argumentsList.find((argument) => argument.startsWith("--exclude-id="));
const excludedId = excludedIdArgument
  ? Number.parseInt(excludedIdArgument.split("=")[1], 10)
  : undefined;
const localOnly = argumentsList.includes("--local-only");
const file = path.resolve(fileArgument);
const sgf = await readFile(file, "utf8");
const validation = validateSgf(sgf);

if (!validation.valid || !validation.root) {
  process.stderr.write("Structural validation failed; duplicate checks were not run.\n");
  for (const item of validation.issues.filter((entry) => entry.severity === "error")) {
    process.stderr.write(`  ${item.code}: ${item.message}\n`);
  }
  process.exit(2);
}

const candidateFingerprint = canonicalProblemFingerprint(validation.root);
const candidateShapes = canonicalRightShapes(validation.root);
const manifest = JSON.parse(
  await readFile(path.join(process.cwd(), "examples", "manifest.json"), "utf8"),
) as Manifest;

let exactLocal: ManifestRecord | undefined;
let closestLocal: { record: ManifestRecord; score: number } | undefined;

for (const record of manifest.problems) {
  if (record.id === excludedId) continue;
  const referenceSgf = await readFile(path.join(process.cwd(), record.sgfFile), "utf8");
  const referenceRoot = parseSgf(referenceSgf);
  if (canonicalProblemFingerprint(referenceRoot) === candidateFingerprint) exactLocal = record;

  const referenceShapes = canonicalRightShapes(referenceRoot);
  const score = Math.max(
    0,
    ...candidateShapes.flatMap((candidate) =>
      referenceShapes.map((reference) => shapeSimilarity(candidate, reference)),
    ),
  );
  if (!closestLocal || score > closestLocal.score) closestLocal = { record, score };
}

process.stdout.write(`Candidate: ${path.relative(process.cwd(), file)}\n`);
process.stdout.write(
  `Local exact match: ${exactLocal ? `GoProblems #${exactLocal.id}` : "none"}\n`,
);
process.stdout.write(
  `Closest local solution shape: ${closestLocal ? `#${closestLocal.record.id} (${Math.round(closestLocal.score * 100)}%)` : "none"}\n`,
);

let duplicate = Boolean(exactLocal);
if (!localOnly) {
  process.stdout.write("Checking GoProblems solution signatures…\n");
  const remote = await findSimilarProblems(sgf, {
    excludedIds: excludedId ? [excludedId] : [],
    limit: 20,
  });
  const radiusIds = remote.radiusTwo.entries.map((entry) => entry.id);
  process.stdout.write(
    `Radius-2 signature matches: ${radiusIds.length ? radiusIds.map((id) => `#${id}`).join(", ") : "none"}\n`,
  );
  process.stdout.write(
    `Top percentage match: ${remote.percentage.topPercentage ?? 0}%${
      remote.percentage.entries[0] ? ` (#${remote.percentage.entries[0].id})` : ""
    }\n`,
  );
  duplicate ||= radiusIds.length > 0 || remote.percentage.topPercentage >= threshold;
}

if (duplicate) {
  process.stderr.write(
    `DUPLICATE GATE: failed. Resolve or replace this problem before scoring the model run.\n`,
  );
  process.exitCode = 1;
} else {
  process.stdout.write("DUPLICATE GATE: passed.\n");
}

