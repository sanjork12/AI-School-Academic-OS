"use client";
import { useEffect, useRef, useState } from "react";
import {
  FileText,
  Upload,
  Check,
  BookOpen,
  ShieldCheck,
  Network,
  LoaderCircle,
} from "lucide-react";
import { demo } from "@/data/demo";
import { Badge, Metrics, NextButton, PageHeading } from "./shared";
export function ImportSyllabus({
  file,
  setFile,
  next,
}: {
  file: string | null;
  setFile: (name: string | null) => void;
  next: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const c = demo.curriculum;
  function choose(selected?: File) {
    if (!selected) return;
    if (
      !selected.name.toLowerCase().endsWith(".pdf") ||
      (selected.type && selected.type !== "application/pdf")
    ) {
      setError("Please select a PDF syllabus.");
      return;
    }
    setError("");
    setFile(selected.name);
  }
  return (
    <>
      <PageHeading
        eyebrow="01 / START WITH YOUR CURRICULUM"
        title="Import a Syllabus"
      >
        Turn curriculum documents into structured, reviewable academic
        intelligence.
      </PageHeading>
      <div className="import-grid">
        <section className="panel upload-panel">
          <div className="section-label">CURRICULUM DOCUMENT</div>
          <div
            className={`drop-zone ${drag ? "drag" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              choose(e.dataTransfer.files[0]);
            }}
          >
            <div className="upload-icon">
              <Upload size={27} />
            </div>
            <h2>Drop syllabus PDF here</h2>
            <p>or click to browse your files</p>
            <button
              className="secondary"
              onClick={() => input.current?.click()}
            >
              Browse files
            </button>
            <input
              ref={input}
              aria-label="Select syllabus PDF"
              className="sr-only"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => choose(e.target.files?.[0])}
            />
            <small>PDF document · File stays on your device</small>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="or-divider">
            <span>OR EXPLORE A WORKED EXAMPLE</span>
          </div>
          <button
            className="demo-selector"
            onClick={() => {
              setError("");
              setFile("Edexcel 4MA1 · Topic 2 demo");
            }}
          >
            <div className="file-icon">
              <FileText size={24} />
            </div>
            <span>
              <strong>Use Demo Syllabus</strong>
              <small>Edexcel International GCSE Mathematics A</small>
            </span>
            <span className="demo-arrow">↗</span>
          </button>
          {file && (
            <div className="selected-file" role="status">
              <Check size={18} />
              <div>
                <strong>{file}</strong>
                <small>
                  {file.includes("· Topic 2 demo")
                    ? "Demo dataset"
                    : "PDF · Local selection"}{" "}
                  · Ready
                </small>
              </div>
            </div>
          )}
          <div className="import-footer">
            <p>
              This walkthrough uses the prepared Topic 2 dataset. Selected PDFs
              are not uploaded or parsed.
            </p>
            <NextButton onClick={next} disabled={!file}>
              Process Syllabus
            </NextButton>
          </div>
        </section>
        <aside className="import-aside">
          <div className="panel dataset-card">
            <div className="section-label">THE DEMO DATASET</div>
            <div className="document-cover">
              <div className="cover-mark">
                <BookOpen size={25} />
              </div>
              <span>PEARSON EDEXCEL</span>
              <h2>Mathematics A</h2>
              <p>International GCSE</p>
              <div className="cover-rule" />
              <div className="flex justify-between">
                <span>SPECIFICATION {c.specification}</span>
                <span>TOPIC {c.topicCode}</span>
              </div>
            </div>
            <dl className="metadata">
              {[
                ["Exam board", c.examBoard],
                ["Qualification", c.qualification],
                ["Subject", c.subject],
                ["Specification", c.specification],
                ["Demo scope", `Topic ${c.topicCode} · ${c.topicName}`],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="trust-note">
            <ShieldCheck size={20} />
            <p>
              <strong>Academic expertise stays in control.</strong>
              <br />
              AI proposes. People review. Only approved decisions shape the
              academic graph.
            </p>
          </div>
        </aside>
      </div>
      <section className="journey-strip">
        <div>
          <FileText />
          <span>
            <strong>Structure the syllabus</strong>
            <small>Preserve official learning objectives</small>
          </span>
        </div>
        <div>
          <ShieldCheck />
          <span>
            <strong>Review with confidence</strong>
            <small>Inspect the evidence behind decisions</small>
          </span>
        </div>
        <div>
          <Network />
          <span>
            <strong>Connect academic skills</strong>
            <small>Build a foundation for what comes next</small>
          </span>
        </div>
      </section>
    </>
  );
}
const stages = [
  "Document identified",
  "Curriculum structure extracted",
  "Official objectives detected",
  "Canonical mapping analysed",
  "Consolidation opportunities checked",
  "Scope differences analysed",
  "Human review queue prepared",
];
export function Processing({ next }: { next: () => void }) {
  const [completed, setCompleted] = useState(0);
  useEffect(() => {
    const timer = setInterval(
      () => setCompleted((n) => Math.min(n + 1, stages.length)),
      420,
    );
    return () => clearInterval(timer);
  }, []);
  const done = completed === stages.length;
  return (
    <>
      <PageHeading
        eyebrow="02 / FROM DOCUMENT TO INTELLIGENCE"
        title={
          done ? "Your curriculum, connected." : "Making sense of the syllabus"
        }
      >
        A replay of the prepared pipeline: official wording is preserved,
        suggestions are reviewable, and academic decisions stay with people.
      </PageHeading>
      <div className="processing-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>AI Processing</h2>
            <Badge tone={done ? "green" : "teal"}>
              {done ? "Complete" : "Demo replay"}
            </Badge>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Demo processing"
            aria-valuenow={completed}
            aria-valuemin={0}
            aria-valuemax={stages.length}
          >
            <div style={{ width: `${(completed / stages.length) * 100}%` }} />
          </div>
          <ol className="processing-list">
            {stages.map((s, i) => (
              <li key={s} className={i < completed ? "done" : ""}>
                {i < completed ? (
                  <Check size={19} />
                ) : i === completed ? (
                  <LoaderCircle className="spin" size={19} />
                ) : (
                  <span className="step-dot" />
                )}
                <span>{s}</span>
              </li>
            ))}
          </ol>
          <p className="muted text-sm">
            Prepared data walkthrough · No live AI call
          </p>
        </section>
        <aside className="processing-note">
          <div className="large-icon">
            <ShieldCheck size={32} />
          </div>
          <h2>
            AI finds the connections.
            <br />
            Experts make the decisions.
          </h2>
          <p>
            A suggestion is not an approved academic skill. Every important
            mapping and consolidation can be inspected before it becomes part of
            the model.
          </p>
          <div className="mini-pipeline">
            Official curriculum <span>→</span> AI proposal <span>→</span> Human
            review
          </div>
        </aside>
      </div>
      <div aria-live="polite">
        {done && (
          <section className="processing-results">
            <Metrics />
            <div className="panel summary-line">
              <div>
                <strong>
                  {demo.processingSummary.mapped} mapped objectives ·{" "}
                  {demo.processingSummary.approvedDecisions} approved human
                  decisions
                </strong>
                <p>
                  {demo.reviewQueue.length} example cases in the Demo Review
                  Queue. These replay already-reviewed decisions; they are not
                  pending audit records.
                </p>
              </div>
              <NextButton onClick={next}>Explore Curriculum</NextButton>
            </div>
          </section>
        )}
      </div>
    </>
  );
}
