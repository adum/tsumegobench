import { mkdir, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { getBoardSize, getMove, parseSgf, stripRootComment } from "../lib/sgf";

const PROBLEM_IDS = [
  // 20–30 kyu
  53750, 18843, 5849, 5973,
  // 10–19 kyu
  39693, 5844, 5922, 10507,
  // 5–9 kyu
  10330, 16482, 8142, 19150,
  // 1–4 kyu
  36582, 32711, 28281, 721,
  // 1 dan
  17778, 20284, 38368, 1311,
] as const;

function normalizeBoardSize(sgf: string, id: number) {
  const root = parseSgf(sgf);
  if (getBoardSize(root) !== 19) {
    throw new Error(`Problem ${id} is not a 19×19 problem.`);
  }
  if (root.properties.SZ?.length) {
    if (root.properties.SZ.length !== 1 || root.properties.SZ[0] !== "19") {
      throw new Error(`Problem ${id} does not explicitly declare SZ[19].`);
    }
    return sgf;
  }

  const normalized = sgf.replace(/^(\uFEFF?\s*\(\s*;)/, "$1SZ[19]");
  if (normalized === sgf) {
    throw new Error(`Problem ${id} could not be normalized to an explicit SZ[19] root.`);
  }
  return normalized;
}

const API_BASE = "https://www.goproblems.com/api/v2/problems";
const workspace = process.cwd();
const examplesDirectory = path.join(workspace, "examples", "canonical-life-and-death");
const appDataDirectory = path.join(workspace, "app", "data");

interface ProblemResponse {
  id: number;
  sgf: string;
  isCanon: boolean;
  isStandard: boolean;
  genre: string;
  specificGenre: string;
  playerColor: "black" | "white";
  rank: { value: number; unit: string; exact: boolean; mark: boolean };
  elo: number;
  author: { id: number; name: string };
  source: string;
  createdAt: string;
  rating: { stars: number; votes: number };
  attempts: { solved: number; failed: number; tries: number };
  avgSolveTimeSeconds: number;
}

const wait = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function fetchProblem(id: number): Promise<ProblemResponse> {
  const response = await fetch(`${API_BASE}/${id}`, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`Problem ${id}: HTTP ${response.status}`);
  return (await response.json()) as ProblemResponse;
}

await mkdir(examplesDirectory, { recursive: true });
await mkdir(appDataDirectory, { recursive: true });

const records = [];
for (const [index, id] of PROBLEM_IDS.entries()) {
  const problem = await fetchProblem(id);
  if (!problem.isCanon || !problem.isStandard || problem.genre !== "life and death") {
    throw new Error(
      `Problem ${id} no longer meets the corpus contract (canonical + standard + life and death).`,
    );
  }

  const normalizedSgf = problem.sgf.replace(/\r\n/g, "\n").trim();
  const withoutRootInstruction = stripRootComment(normalizedSgf).trim();
  const sgf = `${normalizeBoardSize(withoutRootInstruction, id).trim()}\n`;
  const fileName = `gp-${id}.sgf`;
  await writeFile(path.join(examplesDirectory, fileName), sgf, "utf8");
  const root = parseSgf(sgf);
  const firstMoveColors = new Set(
    root.children
      .map(getMove)
      .filter((move): move is NonNullable<ReturnType<typeof getMove>> => Boolean(move))
      .map((move) => move.color),
  );
  if (firstMoveColors.size !== 1) {
    throw new Error(`Problem ${id} does not have one consistent first-player color.`);
  }
  const playerColor = firstMoveColors.has("B") ? "black" : "white";
  if (playerColor !== problem.playerColor) {
    throw new Error(
      `Problem ${id} reports ${problem.playerColor} to play but its SGF starts with ${playerColor}.`,
    );
  }

  records.push({
    id: problem.id,
    label: `Reference #${problem.id}`,
    rank: `${problem.rank.value} ${problem.rank.unit}`,
    rankValue: problem.rank.value,
    rankUnit: problem.rank.unit,
    elo: Math.round(problem.elo),
    playerColor,
    genre: problem.specificGenre || problem.genre,
    author: problem.author.name,
    source: problem.source || "Not listed",
    createdAt: problem.createdAt,
    rating: problem.rating,
    attempts: problem.attempts,
    avgSolveTimeSeconds: problem.avgSolveTimeSeconds,
    canonical: problem.isCanon,
    standard: problem.isStandard,
    sourceUrl: `https://www.goproblems.com/problems/${problem.id}`,
    sgfFile: `examples/canonical-life-and-death/${fileName}`,
    sgf: sgf.trim(),
  });

  process.stdout.write(`synced ${id} (${index + 1}/${PROBLEM_IDS.length})\n`);
  if (index < PROBLEM_IDS.length - 1) await wait(150);
}

const manifest = {
  name: "Canonical life-and-death reference corpus",
  description:
    "Twenty public GoProblems examples on explicit 19×19 boards, distributed evenly from 30 kyu through 1 dan and verified as canonical, standard, and life-and-death when synchronized. Root instructions are removed so the position and side to move stand on their own.",
  boardSize: 19,
  difficultyRange: "30 kyu to 1 dan",
  difficultyBands: {
    "20-30 kyu": 4,
    "10-19 kyu": 4,
    "5-9 kyu": 4,
    "1-4 kyu": 4,
    "1 dan": 4,
  },
  source: "https://www.goproblems.com",
  sourceGuidance: [
    "https://www.goproblems.com/article/problemtypes",
    "https://www.goproblems.com/article/constructionbasics",
    "https://www.goproblems.com/article/bestpractices",
  ],
  count: records.length,
  problems: records.map(({ sgf, ...record }) => {
    void sgf;
    return record;
  }),
};

await writeFile(
  path.join(workspace, "examples", "manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
  "utf8",
);
await writeFile(
  path.join(appDataDirectory, "problems.generated.json"),
  `${JSON.stringify(records, null, 2)}\n`,
  "utf8",
);

const selectedFiles = new Set(PROBLEM_IDS.map((id) => `gp-${id}.sgf`));
for (const entry of await readdir(examplesDirectory, { withFileTypes: true })) {
  if (
    entry.isFile() &&
    /^gp-\d+\.sgf$/i.test(entry.name) &&
    !selectedFiles.has(entry.name)
  ) {
    await rm(path.join(examplesDirectory, entry.name));
  }
}

process.stdout.write(`Wrote ${records.length} verified reference problems.\n`);
