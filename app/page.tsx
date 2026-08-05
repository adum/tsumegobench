import Link from "next/link";

const destinations = [
  {
    href: "/problems",
    number: "01",
    title: "Reference problems",
    detail: "Browse the 20 canonical SGF examples from 30 kyu through 1 dan.",
  },
  {
    href: "/runs",
    number: "02",
    title: "Benchmark runs",
    detail: "Review generated positions, solution trees, and automated results.",
  },
  {
    href: "/evaluation",
    number: "03",
    title: "Evaluation protocol",
    detail: "See the generation, validation, duplicate, and human-review gates.",
  },
  {
    href: "/sources",
    number: "04",
    title: "Sources",
    detail: "Open the Go problem construction guidance and originality APIs.",
  },
];

export default function Home() {
  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span>01</span> PROJECT OVERVIEW</p>
          <h1>AI Go Problem Creation Benchmark</h1>
          <p className="hero-lede">
            This project tests whether AI models can create original, legal, simple life-and-death
            Go problems on 19×19 boards in SGF. It includes reference problems, structural
            validation, duplicate checks, reproducible command-line runs, and human review.
          </p>
          <div className="hero-actions">
            <Link className="primary-action" href="/problems">
              View reference problems <span>→</span>
            </Link>
            <Link className="text-action" href="/runs">Browse benchmark runs</Link>
          </div>
        </div>
        <div className="hero-aside" aria-label="Benchmark facts">
          <dl className="hero-metrics">
            <div><dt>REFERENCE PROBLEMS</dt><dd>20 <small>SGF files</small></dd></div>
            <div><dt>PROBLEMS PER RUN</dt><dd>05 <small>model outputs</small></dd></div>
            <div><dt>DUPLICATE CHECKS</dt><dd>R2 <small>+ percentage</small></dd></div>
            <div><dt>SCORING RUBRIC</dt><dd>100 <small>points</small></dd></div>
          </dl>
        </div>
      </section>

      <section className="home-destinations" aria-label="Benchmark sections">
        {destinations.map((destination) => (
          <Link href={destination.href} key={destination.href}>
            <span>{destination.number}</span>
            <h2>{destination.title}</h2>
            <p>{destination.detail}</p>
            <i aria-hidden="true">→</i>
          </Link>
        ))}
      </section>
    </main>
  );
}
