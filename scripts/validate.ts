import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { validateSgf } from "../lib/validate-sgf";

async function collectSgfFiles(targets: string[]): Promise<string[]> {
  const files: string[] = [];
  for (const target of targets) {
    const resolved = path.resolve(target);
    const details = await stat(resolved);
    if (details.isDirectory()) {
      const entries = await readdir(resolved, { withFileTypes: true });
      files.push(
        ...(await collectSgfFiles(
          entries
            .filter((entry) => entry.isDirectory() || entry.name.toLowerCase().endsWith(".sgf"))
            .map((entry) => path.join(resolved, entry.name)),
        )),
      );
    } else if (resolved.toLowerCase().endsWith(".sgf")) {
      files.push(resolved);
    }
  }
  return files.sort();
}

const targets = process.argv.slice(2).filter((argument) => !argument.startsWith("--"));
if (!targets.length) targets.push("examples/canonical-life-and-death");

const files = await collectSgfFiles(targets);
if (!files.length) {
  process.stderr.write("No SGF files found.\n");
  process.exitCode = 2;
} else {
  let errorCount = 0;
  let warningCount = 0;

  for (const file of files) {
    const report = validateSgf(await readFile(file, "utf8"));
    const relative = path.relative(process.cwd(), file);
    const errors = report.issues.filter((item) => item.severity === "error");
    const warnings = report.issues.filter((item) => item.severity === "warning");
    errorCount += errors.length;
    warningCount += warnings.length;
    const stats = report.stats;
    process.stdout.write(
      `${report.valid ? "PASS" : "FAIL"} ${relative}${
        stats
          ? ` — ${stats.setupStoneCount} setup, ${stats.nodeCount} nodes, ${stats.rightCount} RIGHT`
          : ""
      }\n`,
    );
    for (const item of report.issues) {
      process.stdout.write(
        `  ${item.severity === "error" ? "ERROR" : "WARN "} ${item.code}: ${item.message}${
          item.nodeId ? ` (${item.nodeId})` : ""
        }\n`,
      );
    }
  }

  process.stdout.write(
    `\nChecked ${files.length} SGF files: ${errorCount} errors, ${warningCount} warnings.\n`,
  );
  if (errorCount) process.exitCode = 1;
}

