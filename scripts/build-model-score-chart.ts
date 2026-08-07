import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import {
  buildModelScoreChartData,
  type IndexedRunForChart,
  type ModelMetadataFile,
} from "../lib/model-score-chart";

const projectRoot = process.cwd();
const runIndexFile = path.join(projectRoot, "app", "data", "runs.generated.json");
const metadataFile = path.join(projectRoot, "data", "model-metadata.json");
const outputFile = path.join(projectRoot, "app", "data", "model-scores.generated.json");

const runs = JSON.parse(await readFile(runIndexFile, "utf8")) as IndexedRunForChart[];
const metadata = JSON.parse(await readFile(metadataFile, "utf8")) as ModelMetadataFile;
const chart = buildModelScoreChartData(runs, metadata);

await mkdir(path.dirname(outputFile), { recursive: true });
await writeFile(outputFile, `${JSON.stringify(chart, null, 2)}\n`, "utf8");

process.stdout.write(`Built release-date scores for ${chart.models.length} model(s).\n`);
if (chart.unmatchedModels.length > 0) {
  process.stderr.write(
    `Release metadata is missing for: ${chart.unmatchedModels.join(", ")}\n`,
  );
}
