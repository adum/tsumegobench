import Link from "next/link";
import modelMetadata from "../data/model-metadata.json";
import { ModelScoreChart } from "./components/ModelScoreChart";
import chartData from "./data/model-scores.generated.json";
import runsData from "./data/runs.generated.json";

type IndexedRun = {
  runId: string;
  status: string;
  createdAt: string;
  model: {
    provider: string;
    name: string;
    reasoningEffort?: string | null;
  };
  summary: {
    expectedProblems: number;
    structuralPassed: number;
    automatedGatePassed: number;
  };
  humanReviews: {
    completedProblemReviews: number;
  };
};

const runs = runsData as IndexedRun[];
const recentRuns = [...runs]
  .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
  .slice(0, 6);

function formatDate(value: string, includeTime = false) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit", hour12: false } : {}),
    timeZone: "UTC",
  }).format(new Date(value));
}

function metadataFor(provider: string, name: string) {
  return modelMetadata.models.find((model) =>
    model.aliases.some(
      (alias) => alias.provider === provider && alias.name === name,
    ),
  );
}

const latestUpdate = recentRuns[0]?.createdAt;
const totalRunSlots = runs.reduce(
  (total, run) => total + run.summary.expectedProblems,
  0,
);
const completedReviews = runs.reduce(
  (total, run) => total + run.humanReviews.completedProblemReviews,
  0,
);
const bestAutomatedRun = Math.max(
  0,
  ...runs.map((run) => run.summary.automatedGatePassed),
);
const humanPassingModels = chartData.models.filter(
  (model) => model.passedProblems > 0,
).length;

const resources = [
  {
    href: "/evaluation",
    label: "Methodology",
    detail: "Generation, validation, originality, and human-review gates",
  },
  {
    href: "/problems",
    label: "Reference corpus",
    detail: "20 canonical SGFs spanning 30 kyu through 1 dan",
  },
  {
    href: "/sources",
    label: "Documentation",
    detail: "Prompts, authoring guidance, evaluation rubric, and source APIs",
  },
];

export default function Home() {
  return (
    <main className="benchmark-home">
      <section className="benchmark-masthead" aria-labelledby="benchmark-title">
        <div className="benchmark-masthead-copy">
          <p className="benchmark-kicker">
            <span>Living benchmark</span>
            Version 0.1
          </p>
          <h1 id="benchmark-title">AI Go Problem Creation Benchmark</h1>
          <p className="benchmark-deck">
            A reproducible evaluation of whether AI models can author original,
            legal, and teachable life-and-death Go problems on 19×19 boards in
            SGF. Every result links back to its generated position, solution
            tree, automated checks, and human review.
          </p>
          <nav className="benchmark-quick-links" aria-label="Benchmark shortcuts">
            <Link href="/runs">Explore all runs <span aria-hidden="true">→</span></Link>
            <Link href="/evaluation">Read the method <span aria-hidden="true">→</span></Link>
            <Link href="/problems">Inspect the corpus <span aria-hidden="true">→</span></Link>
          </nav>
        </div>

        <aside className="benchmark-finding" aria-label="Current benchmark finding">
          <p>Current finding</p>
          <strong>
            {humanPassingModels === 0
              ? "No evaluated model has yet cleared every human-review gate."
              : `${humanPassingModels} model${humanPassingModels === 1 ? "" : "s"} have recorded a human-passing result.`}
          </strong>
          <span>
            The strongest automated run advanced {bestAutomatedRun} of 10
            problems to human review.
          </span>
        </aside>
      </section>

      <dl className="benchmark-status-grid" aria-label="Benchmark status">
        <div>
          <dt>Models evaluated</dt>
          <dd>{chartData.models.length}</dd>
        </div>
        <div>
          <dt>Runs indexed</dt>
          <dd>{runs.length}</dd>
        </div>
        <div>
          <dt>Evaluation slots</dt>
          <dd>{totalRunSlots}</dd>
        </div>
        <div>
          <dt>Human reviews</dt>
          <dd>{completedReviews}</dd>
        </div>
        <div className="benchmark-status-date">
          <dt>Latest update</dt>
          <dd>{latestUpdate ? formatDate(latestUpdate) : "Pending"}</dd>
          <small>UTC · indexed artifacts</small>
        </div>
      </dl>

      <div className="home-results-layout">
        <ModelScoreChart />

        <aside className="benchmark-definition" aria-labelledby="definition-title">
          <p className="section-label">Benchmark definition</p>
          <h2 id="definition-title">Four-stage protocol</h2>
          <ol>
            <li>
              <span>01</span>
              <div><strong>Generate</strong><p>Ten SGF problems across five difficulty bands.</p></div>
            </li>
            <li>
              <span>02</span>
              <div><strong>Validate</strong><p>Check syntax, board legality, branches, and solution labels.</p></div>
            </li>
            <li>
              <span>03</span>
              <div><strong>Compare</strong><p>Search the reference corpus and remote shape matches.</p></div>
            </li>
            <li>
              <span>04</span>
              <div><strong>Review</strong><p>Judge correctness, realism, pathing, and originality.</p></div>
            </li>
          </ol>
          <Link className="definition-link" href="/evaluation">
            Full evaluation protocol <span aria-hidden="true">→</span>
          </Link>
        </aside>
      </div>

      <section className="home-run-log" aria-labelledby="run-log-title">
        <header className="home-section-heading">
          <div>
            <p className="section-label">Run log</p>
            <h2 id="run-log-title">Latest benchmark activity</h2>
          </div>
          <Link href="/runs">View all {runs.length} runs <span aria-hidden="true">→</span></Link>
        </header>

        <div className="run-log-table-wrap">
          <table className="run-log-table">
            <thead>
              <tr>
                <th>Started</th>
                <th>Model</th>
                <th>Effort</th>
                <th>Structural</th>
                <th>Automated gate</th>
                <th>Reviewed</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => {
                const model = metadataFor(run.model.provider, run.model.name);
                return (
                  <tr key={run.runId}>
                    <td>
                      <Link href={`/runs?run=${encodeURIComponent(run.runId)}`}>
                        {formatDate(run.createdAt, true)}
                      </Link>
                    </td>
                    <td>
                      <span className="run-log-model">
                        <span className="run-log-provider" aria-hidden="true">
                          {/* Local model-lab marks supplied with the benchmark. */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={model?.icon ?? "/provider-icons/opencode.svg"} alt="" />
                        </span>
                        <span><strong>{model?.displayName ?? run.model.name}</strong><small>{model?.family ?? run.model.provider}</small></span>
                      </span>
                    </td>
                    <td>{run.model.reasoningEffort ?? "default"}</td>
                    <td>{run.summary.structuralPassed}/{run.summary.expectedProblems}</td>
                    <td>{run.summary.automatedGatePassed}/{run.summary.expectedProblems}</td>
                    <td>{run.humanReviews.completedProblemReviews}/{run.summary.expectedProblems}</td>
                    <td><span className={`run-log-status ${run.status}`}>{run.status}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="benchmark-resources" aria-labelledby="resources-title">
        <div className="benchmark-resources-intro">
          <p className="section-label">Audit the benchmark</p>
          <h2 id="resources-title">Methods and source material</h2>
          <p>Results are useful only when the task, artifacts, and review criteria remain inspectable.</p>
        </div>
        <div className="benchmark-resource-list">
          {resources.map((resource, index) => (
            <Link href={resource.href} key={resource.href}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{resource.label}</strong>
              <p>{resource.detail}</p>
              <i aria-hidden="true">→</i>
            </Link>
          ))}
          <a href="https://github.com/adum/tsumegobench" target="_blank" rel="noreferrer">
            <span>04</span>
            <strong>Repository</strong>
            <p>Source code, benchmark inputs, run artifacts, and schemas</p>
            <i aria-hidden="true">↗</i>
          </a>
        </div>
      </section>
    </main>
  );
}
