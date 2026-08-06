import type { Metadata } from "next";
import { EvaluationProtocol } from "../components/EvaluationProtocol";

export const metadata: Metadata = { title: "Benchmark process · Tsumego Bench" };

export default function EvaluationPage() {
  return <main className="route-main"><EvaluationProtocol /></main>;
}
