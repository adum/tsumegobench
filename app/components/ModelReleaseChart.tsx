import Link from "next/link";
import type { CSSProperties } from "react";
import { topScoringModelsForLegend } from "@/lib/model-score-chart";
import chartData from "../data/model-scores.generated.json";

const DAY = 24 * 60 * 60 * 1000;
const yTicks = [0, 2, 4, 6, 8, 10];

function dateValue(date: string) {
  return new Date(`${date}T00:00:00Z`).getTime();
}

function formatDate(value: number, includeYear = false) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    ...(includeYear ? { year: "numeric" } : {}),
    timeZone: "UTC",
  }).format(new Date(value));
}

function scoreLabel(score: number) {
  return Number.isInteger(score) ? `${score}` : score.toFixed(1);
}

export function ModelReleaseChart() {
  const models = chartData.models;
  if (models.length === 0) return null;
  const legendModels = topScoringModelsForLegend(models, {
    limit: 6,
    minimumScore: 1,
  });

  const releaseDates = models.map((model) => dateValue(model.releaseDate));
  const earliestRelease = Math.min(...releaseDates);
  const latestRelease = Math.max(...releaseDates);
  const releaseSpan = Math.max(DAY, latestRelease - earliestRelease);
  const datePadding = Math.max(7 * DAY, releaseSpan * 0.12);
  const chartStart = earliestRelease - datePadding;
  const chartEnd = latestRelease + datePadding;
  const chartSpan = chartEnd - chartStart;
  const xTicks = Array.from({ length: 5 }, (_, index) =>
    chartStart + (chartSpan * index) / 4,
  );

  const scoreGroups = new Map<number, Array<(typeof models)[number]>>();
  for (const model of models) {
    scoreGroups.set(model.score, [...(scoreGroups.get(model.score) ?? []), model]);
  }

  const pointPositions = new Map<string, { x: number; offset: number }>();
  for (const scoreModels of scoreGroups.values()) {
    const sortedModels = [...scoreModels].sort((left, right) =>
      left.releaseDate.localeCompare(right.releaseDate),
    );
    let clusterStart = 0;
    while (clusterStart < sortedModels.length) {
      let clusterEnd = clusterStart + 1;
      while (
        clusterEnd < sortedModels.length &&
        dateValue(sortedModels[clusterEnd].releaseDate) -
          dateValue(sortedModels[clusterEnd - 1].releaseDate) <=
          2 * DAY
      ) {
        clusterEnd += 1;
      }

      const cluster = sortedModels.slice(clusterStart, clusterEnd);
      const averageDate =
        cluster.reduce((total, model) => total + dateValue(model.releaseDate), 0) /
        cluster.length;
      const x = ((averageDate - chartStart) / chartSpan) * 100;
      cluster.forEach((model, index) => {
        pointPositions.set(model.id, {
          x,
          offset: (index - (cluster.length - 1) / 2) * 42,
        });
      });
      clusterStart = clusterEnd;
    }
  }

  return (
    <section className="home-model-chart" aria-labelledby="model-chart-title">
      <div className="model-chart-heading">
        <div>
          <p className="eyebrow">BENCHMARK TRAJECTORY</p>
          <h2 id="model-chart-title">All LLMs By Release Date</h2>
        </div>
        <p>
          Each model is plotted once by public release date, using its best
          human-reviewed run and a difficulty-capped score out of 10.
        </p>
      </div>

      <div className="model-chart-layout">
        <div
          className="model-chart-plot"
          role="img"
          aria-label={`Model scores from 0 to 10 by release date. ${models
            .map(
              (model) =>
                `${model.displayName}, released ${formatDate(dateValue(model.releaseDate), true)}, score ${scoreLabel(model.score)} out of 10`,
            )
            .join(". ")}.`}
        >
          <span className="model-chart-y-title">Score out of 10</span>
          <div className="model-chart-field">
            {yTicks.map((tick) => (
              <span
                className={`model-chart-y-grid${tick === 0 ? " baseline" : ""}`}
                key={tick}
                style={{ bottom: `${tick * 10}%` }}
              >
                <i>{tick}</i>
              </span>
            ))}

            {xTicks.map((tick, index) => (
              <span
                className="model-chart-x-tick"
                key={tick}
                style={{ left: `${index * 25}%` }}
              >
                <i>{formatDate(tick, index === 0 || index === xTicks.length - 1)}</i>
              </span>
            ))}

            {models.map((model) => {
              const position = pointPositions.get(model.id) ?? {
                x: ((dateValue(model.releaseDate) - chartStart) / chartSpan) * 100,
                offset: 0,
              };
              const pointStyle = {
                left: `calc(${position.x}% + ${position.offset}px)`,
                bottom: `${model.score * 10}%`,
              } as CSSProperties;
              const accessibleLabel = `${model.displayName}: ${scoreLabel(model.score)} out of 10, released ${formatDate(dateValue(model.releaseDate), true)}`;

              return (
                <Link
                  aria-label={`${accessibleLabel}. Open best run.`}
                  className="model-chart-point"
                  href={`/runs?run=${encodeURIComponent(model.bestRunId)}`}
                  key={model.id}
                  style={pointStyle}
                  title={accessibleLabel}
                >
                  <span className="model-chart-point-mark">
                    {/* Local model-lab marks supplied with the benchmark. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={model.icon} alt="" aria-hidden="true" />
                  </span>
                </Link>
              );
            })}
          </div>
          <span className="model-chart-x-title">Model release date</span>
        </div>

        <ol className="model-chart-legend" aria-label="Top scoring models">
          {legendModels.map((model) => (
            <li key={model.id}>
              <Link href={`/runs?run=${encodeURIComponent(model.bestRunId)}`}>
                <span className="model-chart-legend-mark" aria-hidden="true">
                  {/* Local model-lab marks supplied with the benchmark. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={model.icon} alt="" />
                </span>
                <span className="model-chart-legend-copy">
                  <strong>{model.displayName}</strong>
                  <small>
                    {model.family} / {formatDate(dateValue(model.releaseDate), true)}
                  </small>
                </span>
                <b>{scoreLabel(model.score)}<small>/10</small></b>
              </Link>
            </li>
          ))}
        </ol>
      </div>

      {chartData.unmatchedModels.length > 0 ? (
        <p className="model-chart-metadata-note">
          Release metadata is still needed for {chartData.unmatchedModels.length} model
          {chartData.unmatchedModels.length === 1 ? "" : "s"}.
        </p>
      ) : null}
    </section>
  );
}
