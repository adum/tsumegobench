import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sources · Tsumego Bench" };

const constructionSources = [
  ["Problem types", "Canonical forms and problem classifications.", "https://www.goproblems.com/article/problemtypes"],
  ["Construction basics", "How to construct clear, valid Go problems.", "https://www.goproblems.com/article/constructionbasics"],
  ["Best practices", "Guidance for solution trees and useful variations.", "https://www.goproblems.com/article/bestpractices"],
];

const originalitySources = [
  ["API access", "GoProblems API conventions used by the evaluator.", "https://www.goproblems.com/article/api"],
  ["Solution signatures", "How problem and solution similarity are represented.", "https://www.goproblems.com/article/solutionsignatures"],
];

export default function SourcesPage() {
  return (
    <main className="source-page">
      <header className="page-intro">
        <p className="eyebrow"><span>04</span> SOURCES</p>
        <h1>Guidance and APIs</h1>
        <p>
          The authoring prompt and evaluator are based on the GoProblems construction guidance,
          while every reference problem retains its original author and source URL in the corpus manifest.
        </p>
        <a
          className="source-repository-link"
          href="https://github.com/adum/tsumegobench"
          target="_blank"
          rel="noreferrer"
        >
          <span>GitHub repository</span>
          <strong>adum/tsumegobench</strong>
          <i aria-hidden="true">↗</i>
        </a>
      </header>
      <div className="source-groups">
        <section aria-labelledby="construction-sources">
          <span className="panel-label">PROBLEM CONSTRUCTION</span>
          <h2 id="construction-sources">Authoring guidance</h2>
          <div className="source-list">
            {constructionSources.map(([title, detail, href]) => (
              <a href={href} key={href}>
                <strong>{title}</strong><p>{detail}</p><span>Open ↗</span>
              </a>
            ))}
          </div>
        </section>
        <section aria-labelledby="originality-sources">
          <span className="panel-label">ORIGINALITY</span>
          <h2 id="originality-sources">Duplicate detection</h2>
          <div className="source-list">
            {originalitySources.map(([title, detail, href]) => (
              <a href={href} key={href}>
                <strong>{title}</strong><p>{detail}</p><span>Open ↗</span>
              </a>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
