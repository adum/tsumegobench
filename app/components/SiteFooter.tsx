import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-identity">
        <span className="wordmark-stone" aria-hidden="true" />
        <p><strong>Tsumego Bench</strong><br />A reproducible benchmark for AI-authored life-and-death Go problems.</p>
      </div>
      <div className="footer-links">
        <span>EXPLORE</span>
        <Link href="/runs">Results and runs</Link>
        <Link href="/problems">Reference corpus</Link>
        <Link href="/evaluation">Evaluation method</Link>
      </div>
      <div className="footer-links">
        <span>REPRODUCE</span>
        <Link href="/sources">Documentation and APIs</Link>
        <a href="https://github.com/adum/tsumegobench">GitHub repository ↗</a>
      </div>
      <p className="footer-note">v0.1 · Reference authors and source URLs remain attached to the corpus manifest.</p>
    </footer>
  );
}
