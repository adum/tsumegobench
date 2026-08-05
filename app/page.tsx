import { ProblemWorkbench } from "./components/ProblemWorkbench";

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="wordmark" href="#top" aria-label="Tsumego Bench home">
          <span className="wordmark-stone" aria-hidden="true" />
          <span>TSUMEGO / BENCH</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#workbench">Problems</a>
          <a href="#protocol">Evaluation</a>
          <a href="#sources">Sources</a>
        </nav>
        <span className="header-status">v0.1 · LOCAL + API</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span>01</span> PROJECT OVERVIEW</p>
          <h1>AI Go Problem Creation Benchmark</h1>
          <p className="hero-lede">
            This project tests whether AI models can create original, legal, simple life-and-death
            Go problems in SGF. It includes reference problems, structural validation, duplicate
            checks, and human review.
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#workbench">View reference problems <span>↓</span></a>
            <a className="text-action" href="#protocol">View evaluation protocol</a>
          </div>
        </div>
        <div className="hero-aside" aria-label="Benchmark facts">
          <div className="hero-mark" aria-hidden="true">
            <span className="hero-black-stone" />
            <span className="hero-white-stone" />
            <span className="hero-line horizontal" />
            <span className="hero-line vertical" />
          </div>
          <dl className="hero-metrics">
            <div><dt>REFERENCE PROBLEMS</dt><dd>20 <small>SGF files</small></dd></div>
            <div><dt>PROBLEMS PER RUN</dt><dd>05 <small>model outputs</small></dd></div>
            <div><dt>DUPLICATE CHECKS</dt><dd>R2 <small>+ percentage</small></dd></div>
            <div><dt>SCORING RUBRIC</dt><dd>100 <small>points</small></dd></div>
          </dl>
        </div>
      </section>

      <div className="principle-strip" role="note">
        <span>SGF VALIDATION</span>
        <span aria-hidden="true">◆</span>
        <span>DUPLICATE CHECKS</span>
        <span aria-hidden="true">◆</span>
        <span>HUMAN GO REVIEW</span>
      </div>

      <ProblemWorkbench />

      <section className="protocol-section" id="protocol" aria-labelledby="protocol-title">
        <div className="protocol-intro">
          <p className="eyebrow"><span>02</span> EVALUATION</p>
          <h2 id="protocol-title">Evaluation protocol</h2>
          <p>
            Each model receives the same prompt and 20 reference SGFs. The first output is
            preserved; repaired output is recorded as a separate run.
          </p>
        </div>
        <ol className="protocol-grid">
          <li>
            <span className="protocol-number">01</span>
            <div className="protocol-icon generate" aria-hidden="true"><i /><i /><i /></div>
            <h3>Generate</h3>
            <p>Request five simple local life-and-death problems in SGF.</p>
            <small>RAW OUTPUT SAVED</small>
          </li>
          <li>
            <span className="protocol-number">02</span>
            <div className="protocol-icon validate" aria-hidden="true">✓</div>
            <h3>Validate</h3>
            <p>Parse structure, alternate moves, simulate captures, and enforce the simplicity envelope.</p>
            <small>HARD GATE</small>
          </li>
          <li>
            <span className="protocol-number">03</span>
            <div className="protocol-icon compare" aria-hidden="true"><i /><i /></div>
            <h3>Deduplicate</h3>
            <p>Canonical local fingerprints plus live radius-2 and percentage searches.</p>
            <small>HARD GATE · ≥90% FAILS</small>
          </li>
          <li>
            <span className="protocol-number">04</span>
            <div className="protocol-icon judge" aria-hidden="true"><i /></div>
            <h3>Judge</h3>
            <p>A competent player checks best resistance, missing moves, clarity, and teaching value.</p>
            <small>100-POINT RUBRIC</small>
          </li>
        </ol>
        <div className="protocol-footer">
          <p><strong>Report:</strong> acceptance rate and mean score, with rejected problems scored as zero.</p>
          <p><strong>Limitation:</strong> structural validation does not establish life-and-death correctness; human review is required.</p>
        </div>
      </section>

      <footer className="site-footer" id="sources">
        <div>
          <span className="wordmark-stone" aria-hidden="true" />
          <p><strong>Tsumego Bench</strong><br />Benchmark for AI-generated life-and-death Go problems.</p>
        </div>
        <div className="footer-links">
          <span>SOURCE GUIDANCE</span>
          <a href="https://www.goproblems.com/article/problemtypes">Problem types ↗</a>
          <a href="https://www.goproblems.com/article/constructionbasics">Construction basics ↗</a>
          <a href="https://www.goproblems.com/article/bestpractices">Best practices ↗</a>
        </div>
        <div className="footer-links">
          <span>ORIGINALITY</span>
          <a href="https://www.goproblems.com/article/api">API access ↗</a>
          <a href="https://www.goproblems.com/article/solutionsignatures">Solution signatures ↗</a>
        </div>
        <p className="footer-note">Reference authors and sources are retained in the corpus manifest.</p>
      </footer>
    </main>
  );
}
