import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="wordmark" href="/" aria-label="Tsumego Bench home">
        <span className="wordmark-stone" aria-hidden="true" />
        <span>TSUMEGO / BENCH</span>
      </Link>
      <nav aria-label="Primary navigation">
        <Link href="/problems">Problems</Link>
        <Link href="/runs">Runs</Link>
        <Link href="/evaluation">Evaluation</Link>
        <Link href="/sources">Sources</Link>
      </nav>
      <span className="header-status">v0.1 · LOCAL + API</span>
    </header>
  );
}
