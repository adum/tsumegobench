import Link from "next/link";
import chartData from "../data/model-scores.generated.json";
import runsData from "../data/runs.generated.json";

type ResultRun = {
  runId: string;
  createdAt: string;
  summary: {
    expectedProblems: number;
    structuralPassed: number;
    automatedGatePassed: number;
  };
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

function scoreLabel(score: number) {
  return Number.isInteger(score) ? `${score}.0` : score.toFixed(1);
}

export function ModelScoreChart() {
  const runById = new Map(
    (runsData as ResultRun[]).map((run) => [run.runId, run]),
  );
  const models = chartData.models
    .map((model) => ({ ...model, bestRun: runById.get(model.bestRunId) }))
    .sort(
      (left, right) =>
        right.score - left.score ||
        (right.bestRun?.summary.automatedGatePassed ?? 0) -
          (left.bestRun?.summary.automatedGatePassed ?? 0) ||
        left.displayName.localeCompare(right.displayName),
    );

  if (models.length === 0) return null;

  return (
    <section className="model-results" aria-labelledby="model-results-title">
      <header className="model-results-heading">
        <div>
          <p className="section-label">Current results</p>
          <h2 id="model-results-title">Model summary</h2>
        </div>
        <p>
          Each row uses that model’s best human-reviewed run. Select a model to
          inspect its generated files and gate-by-gate evidence.
        </p>
      </header>

      <div className="model-results-table-wrap">
        <table className="model-results-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Human-passed</th>
              <th>Automated gate</th>
              <th>Structural</th>
              <th>Runs</th>
              <th>Latest best</th>
            </tr>
          </thead>
          <tbody>
            {models.map((model) => {
              const problemCount = model.bestRun?.summary.expectedProblems ?? model.problemCount;
              const automated = model.bestRun?.summary.automatedGatePassed ?? 0;
              const structural = model.bestRun?.summary.structuralPassed ?? 0;
              const meterWidth = Math.max(0, Math.min(100, model.score * 10));

              return (
                <tr key={model.id}>
                  <td>
                    <Link
                      className="model-result-name"
                      href={`/runs?run=${encodeURIComponent(model.bestRunId)}`}
                    >
                      <span className="model-result-mark" aria-hidden="true">
                        {/* Local model-lab marks supplied with the benchmark. */}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={model.icon} alt="" />
                      </span>
                      <span><strong>{model.displayName}</strong><small>{model.family}</small></span>
                    </Link>
                  </td>
                  <td className="model-result-score">
                    <span><strong>{model.passedProblems}/{model.problemCount}</strong><small>{scoreLabel(model.score)} / 10</small></span>
                    <span className="model-result-meter" aria-hidden="true"><i style={{ width: `${meterWidth}%` }} /></span>
                  </td>
                  <td><strong>{automated}</strong><small> / {problemCount}</small></td>
                  <td><strong>{structural}</strong><small> / {problemCount}</small></td>
                  <td>{model.runCount}</td>
                  <td>{formatDate(model.bestRunCreatedAt)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="model-results-note">
        <span>Score definition</span>
        A problem counts only after completed human review confirms validity,
        realism, originality, and a well-pathed solution tree.
      </footer>

      {chartData.unmatchedModels.length > 0 ? (
        <p className="model-results-warning">
          Release metadata is still needed for {chartData.unmatchedModels.length} model
          {chartData.unmatchedModels.length === 1 ? "" : "s"}.
        </p>
      ) : null}
    </section>
  );
}
