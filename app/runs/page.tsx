import type { Metadata } from "next";
import { RunBrowser } from "../components/RunBrowser";

export const metadata: Metadata = { title: "Benchmark runs · Tsumego Bench" };

export default function RunsPage() {
  return <main className="route-main"><RunBrowser /></main>;
}
