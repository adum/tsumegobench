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
          <a href="#workbench">Reference lab</a>
          <a href="#protocol">Protocol</a>
          <a href="#sources">Sources</a>
        </nav>
        <span className="header-status">v0.1 · LOCAL + API</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span>01</span> AI GO-PROBLEM CREATION TESTBED</p>
          <h1>Can a model invent a Go problem <em>worth solving?</em></h1>
          <p className="hero-lede">
            A narrow, evidence-first benchmark for original life-and-death creation. Parse the
            SGF, replay every branch, reject familiar shapes, then let a Go player judge the idea.
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#workbench">Open the reference lab <span>↓</span></a>
            <a className="text-action" href="#protocol">Read the four-stage protocol</a>
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
            <div><dt>REFERENCE SET</dt><dd>20 <small>verified SGFs</small></dd></div>
            <div><dt>DEFAULT RUN</dt><dd>05 <small>new problems</small></dd></div>
            <div><dt>DUPLICATE GATE</dt><dd>R2 <small>+ percentage</small></dd></div>
            <div><dt>REVIEW SCALE</dt><dd>100 <small>human-scored</small></dd></div>
          </dl>
        </div>
      </section>

      <div className="principle-strip" role="note">
        <span>STRUCTURE IS AUTOMATED</span>
        <span aria-hidden="true">◆</span>
        <span>ORIGINALITY IS SEARCHED</span>
        <span aria-hidden="true">◆</span>
        <span>LIFE &amp; DEATH IS REVIEWED</span>
      </div>

      <ProblemWorkbench />

      <section className="protocol-section" id="protocol" aria-labelledby="protocol-title">
        <div className="protocol-intro">
          <p className="eyebrow"><span>02</span> CONTROLLED EVALUATION</p>
          <h2 id="protocol-title">One prompt. Four gates. No quiet repairs.</h2>
          <p>
            Each model gets the same prompt and examples. First attempts stay immutable; repaired
            outputs become a separate run. Reliability matters as much as a single clever shape.
          </p>
        </div>
        <ol className="protocol-grid">
          <li>
            <span className="protocol-number">01</span>
            <div className="protocol-icon generate" aria-hidden="true"><i /><i /><i /></div>
            <h3>Generate</h3>
            <p>Five local, simple SGFs from the controlled prompt and identical reference set.</p>
            <small>RAW OUTPUT PRESERVED</small>
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
          <p><strong>Primary report:</strong> acceptance rate + mean score with rejects counted as zero.</p>
          <p><strong>Known boundary:</strong> this version does not pretend static validation proves life.</p>
        </div>
      </section>

      <footer className="site-footer" id="sources">
        <div>
          <span className="wordmark-stone" aria-hidden="true" />
          <p><strong>Tsumego Bench</strong><br />A small framework for a difficult creative claim.</p>
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

