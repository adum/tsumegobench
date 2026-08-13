import type { Metadata } from "next";
import { RunBrowser, type BenchmarkRun } from "../components/RunBrowser";
import runData from "../data/runs.generated.json";

export const metadata: Metadata = { title: "Benchmark runs · Tsumego Bench" };

export default function RunsPage() {
  return (
    <main className="route-main">
      <RunBrowser runs={runData as BenchmarkRun[]} />
    </main>
  );
}
