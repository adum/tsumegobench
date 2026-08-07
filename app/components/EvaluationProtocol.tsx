export function EvaluationProtocol() {
  return (
    <section className="protocol-section" aria-labelledby="protocol-title">
      <div className="protocol-intro">
        <p className="eyebrow"><span>03</span> PROCESS</p>
        <h1 id="protocol-title">Benchmark process</h1>
        <p>
          The runner gives each model the same snapshotted packet through a non-interactive CLI
          harness. The first files and CLI log are preserved; repaired output is recorded as a
          separate run.
        </p>
      </div>
      <ol className="protocol-grid">
        <li>
          <span className="protocol-number">01</span>
          <div className="protocol-icon generate" aria-hidden="true"><i /><i /><i /></div>
          <h2>Generate</h2>
          <p>Invoke a selected model through Codex CLI, Claude CLI, Grok CLI, or OpenCode CLI and write ten SGFs into an isolated run.</p>
          <small>FILES + EVENT LOG SAVED</small>
        </li>
        <li>
          <span className="protocol-number">02</span>
          <div className="protocol-icon validate" aria-hidden="true">✓</div>
          <h2>Validate</h2>
          <p>Parse structure, alternate moves, simulate captures, and enforce the simplicity envelope.</p>
          <small>HARD GATE</small>
        </li>
        <li>
          <span className="protocol-number">03</span>
          <div className="protocol-icon compare" aria-hidden="true"><i /><i /></div>
          <h2>Deduplicate</h2>
          <p>Canonical local fingerprints plus live radius-2 and percentage searches.</p>
          <small>HARD GATE · ≥90% FAILS</small>
        </li>
        <li>
          <span className="protocol-number">04</span>
          <div className="protocol-icon judge" aria-hidden="true"><i /></div>
          <h2>Judge</h2>
          <p>A competent player checks solution and refutation coverage, endpoint judgment, clarity, teaching value, and actual difficulty.</p>
          <small>100-POINT RUBRIC</small>
        </li>
      </ol>
      <div className="protocol-footer">
        <p><strong>Report:</strong> difficulty-capped acceptance: at most two 20–30 kyu and two 10–19 kyu problems receive credit; harder problems are uncapped.</p>
        <p><strong>Limitation:</strong> structural validation does not establish life-and-death correctness; human review is required.</p>
      </div>
    </section>
  );
}
