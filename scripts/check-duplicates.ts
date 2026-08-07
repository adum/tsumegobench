import { readFile } from "node:fs/promises";
import path from "node:path";
import { findBuiltInSetupDuplicate } from "../lib/common-setup-duplicates";
import { checkProblemDuplicates, loadDuplicateCorpus } from "../lib/duplicate-check";
import { validateSgf } from "../lib/validate-sgf";

const argumentsList = process.argv.slice(2);
const fileArgument = argumentsList.find((argument) => !argument.startsWith("--"));
if (!fileArgument) {
  process.stderr.write(
    "Usage: npm run duplicates -- runs/run-name/outputs/problem.sgf [--local-only] [--threshold=90] [--exclude-id=123]\n",
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
const builtInSetupMatch = validation.root
  ? findBuiltInSetupDuplicate(validation.root)
  : null;

if (!validation.root || (!validation.valid && !builtInSetupMatch)) {
  process.stderr.write("Structural validation failed; duplicate checks were not run.\n");
  for (const item of validation.issues.filter((entry) => entry.severity === "error")) {
    process.stderr.write(`  ${item.code}: ${item.message}\n`);
  }
  process.exit(2);
}

const report = await checkProblemDuplicates(
  sgf,
  validation.root,
  await loadDuplicateCorpus(),
  {
    remote: !localOnly,
    failThreshold: threshold,
    excludedIds: excludedId ? [excludedId] : [],
  },
);

process.stdout.write(`Candidate: ${path.relative(process.cwd(), file)}\n`);
process.stdout.write(
  `Built-in common setup: ${
    report.builtInSetupMatch
      ? `${report.builtInSetupMatch.label} (${report.builtInSetupMatch.id})`
      : "none"
  }\n`,
);
process.stdout.write(
  `Local exact match: ${report.exactLocalMatch ? `GoProblems #${report.exactLocalMatch.id}` : "none"}\n`,
);
process.stdout.write(
  `Closest local solution shape: ${
    report.closestLocalShape
      ? `#${report.closestLocalShape.id} (${Math.round(report.closestLocalShape.percentage)}%)`
      : "none"
  }\n`,
);

if (!localOnly) {
  process.stdout.write(
    report.remote.error
      ? `Remote duplicate check unavailable: ${report.remote.error}\n`
      : `Radius-2 signature matches: ${
          report.remote.radiusTwoMatches.length
            ? report.remote.radiusTwoMatches.map(({ id }) => `#${id}`).join(", ")
            : "none"
        }\nTop percentage match: ${report.remote.topPercentage ?? 0}%${
          report.remote.topMatchId ? ` (#${report.remote.topMatchId})` : ""
        }\n`,
  );
}

if (report.status === "fail") {
  process.stderr.write(
    "DUPLICATE GATE: failed. Resolve or replace this problem before scoring the model run.\n",
  );
  process.exitCode = 1;
} else if (report.status === "manual_review") {
  process.stdout.write("DUPLICATE GATE: manual comparison required.\n");
} else if (!localOnly && report.remote.status === "error") {
  process.stderr.write("DUPLICATE GATE: incomplete because the remote check failed.\n");
  process.exitCode = 2;
} else if (report.status === "not_run") {
  process.stdout.write("DUPLICATE GATE: local checks passed; remote result not available.\n");
} else {
  process.stdout.write("DUPLICATE GATE: passed.\n");
}
