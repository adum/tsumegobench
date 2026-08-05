import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div>
        <span className="wordmark-stone" aria-hidden="true" />
        <p><strong>Tsumego Bench</strong><br />Benchmark for AI-generated life-and-death Go problems.</p>
      </div>
      <div className="footer-links">
        <span>BENCHMARK</span>
        <Link href="/problems">Reference problems</Link>
        <Link href="/runs">Generated runs</Link>
        <Link href="/evaluation">Evaluation protocol</Link>
      </div>
      <div className="footer-links">
        <span>DOCUMENTATION</span>
        <Link href="/sources">Sources and APIs</Link>
        <a href="https://github.com/adum/tsumegobench">GitHub repository ↗</a>
      </div>
      <p className="footer-note">Reference authors and sources are retained in the corpus manifest.</p>
    </footer>
  );
}
