import type { Metadata } from "next";
import { ProblemWorkbench } from "../components/ProblemWorkbench";

export const metadata: Metadata = { title: "Reference problems · Tsumego Bench" };

export default function ProblemsPage() {
  return <main className="route-main"><ProblemWorkbench /></main>;
}
