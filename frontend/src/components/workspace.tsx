"use client";
import { useRef, useState } from "react";
import {
  BookOpen,
  Upload,
  Layers,
  Network,
  ScanLine,
  ShieldCheck,
  RotateCcw,
  ChevronRight,
} from "lucide-react";
import { demo } from "@/data/demo";
import type { LocalReview } from "@/data/types";
import { ImportSyllabus, Processing } from "./import-processing";
import { Curriculum } from "./curriculum";
import { Review } from "./review";
import { ApprovedGraph } from "./approved-graph";
const steps = [
  { name: "Import", detail: "Start with the syllabus", icon: Upload },
  { name: "Process", detail: "Find the structure", icon: ScanLine },
  { name: "Curriculum", detail: "Explore the objectives", icon: BookOpen },
  { name: "Review", detail: "Apply expert judgement", icon: ShieldCheck },
  { name: "Approved Graph", detail: "Connect academic skills", icon: Network },
];
function initialReviews(): Record<string, LocalReview> {
  return Object.fromEntries(
    demo.reviewQueue.map((c) => [
      c.id,
      {
        status: "Awaiting demo review",
        name: c.name,
        domain: c.domain,
        description: c.description,
      },
    ]),
  );
}
export function Workspace() {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState<string | null>(null);
  const [reviews, setReviews] = useState(initialReviews);
  const [session, setSession] = useState(0);
  const main = useRef<HTMLElement>(null);
  function go(n: number) {
    setStep(n);
    window.scrollTo({ top: 0 });
    requestAnimationFrame(() => main.current?.focus());
  }
  function reset() {
    setReviews(initialReviews());
    setFile(null);
    setSession((s) => s + 1);
    go(0);
  }
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            go(0);
          }}
          aria-label="Academic Intelligence home"
        >
          <span className="brand-mark">
            <Layers size={23} />
          </span>
          <span>
            Academic{" "}
            <br />
            Intelligence<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace-label">CURRICULUM WORKSPACE</div>
        <div className="workspace-chip">
          <div>MA</div>
          <span>
            Mathematics A<small>Edexcel · International GCSE</small>
          </span>
        </div>
        <div className="sidebar-section-label">YOUR WORKFLOW</div>
        <nav aria-label="Workflow">
          {steps.map((s, i) => (
            <button
              key={s.name}
              onClick={() => go(i)}
              aria-current={step === i ? "step" : undefined}
              className={`workflow-item ${step === i ? "active" : ""}`}
            >
              <span className="workflow-icon">
                <s.icon size={19} />
              </span>
              <span>
                <strong>
                  {i + 1}. {s.name}
                </strong>
                <small>{s.detail}</small>
              </span>
              {step === i && (
                <ChevronRight className="workflow-chevron" size={15} />
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-principle">
            <ShieldCheck size={19} />
            <strong>
              Human expertise.
              <br />
              AI assistance.
            </strong>
            <p>
              Academic decisions belong
              <br />
              to academic experts.
            </p>
          </div>
          <div className="demo-version">
            <span className="status-dot" />
            INTERACTIVE DEMO <span>v0.1</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace
            <ChevronRight size={14} />
            <strong>Curriculum Intelligence</strong>
          </div>
          <button className="reset-button" onClick={reset}>
            <RotateCcw size={15} />
            Reset Demo
          </button>
        </header>
        <main
          ref={main}
          tabIndex={-1}
          id="main-content"
          className="main-content"
        >
          <div className="dataset-line">
            <span className="dataset-dot" />
            Demo dataset: Edexcel International GCSE Mathematics A (4MA1), Topic
            2
          </div>
          <div key={session}>
            {step === 0 && (
              <ImportSyllabus
                file={file}
                setFile={setFile}
                next={() => go(1)}
              />
            )}{" "}
            {step === 1 && <Processing next={() => go(2)} />}{" "}
            {step === 2 && <Curriculum next={() => go(3)} />}{" "}
            {step === 3 && (
              <Review
                reviews={reviews}
                update={(id, v) => setReviews((r) => ({ ...r, [id]: v }))}
                next={() => go(4)}
              />
            )}{" "}
            {step === 4 && <ApprovedGraph reviews={reviews} />}
          </div>
          <footer className="page-footer">
            <span>Academic Intelligence</span>
            <span>
              Official curriculum → AI proposals → Human review → Approved graph
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
