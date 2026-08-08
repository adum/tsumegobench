import Link from "next/link";
import runsData from "../data/runs.generated.json";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="wordmark" href="/" aria-label="Tsumego Bench home">
        <span className="wordmark-stone" aria-hidden="true" />
        <span>TSUMEGO / BENCH</span>
      </Link>
      <nav aria-label="Primary navigation">
        <Link href="/">Overview</Link>
        <Link href="/runs">Results</Link>
        <Link href="/problems">Example Problems</Link>
        <Link href="/evaluation">Method</Link>
        <Link href="/sources">Sources</Link>
      </nav>
      <span className="header-status">v0.1 · {runsData.length} runs</span>
    </header>
  );
}
