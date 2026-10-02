"use client";
import { useEffect, useRef, useState } from "react";
import { Check, Pencil, X, ArrowDown, ShieldCheck } from "lucide-react";
import { demo } from "@/data/demo";
import type { LocalReview, ReviewCase } from "@/data/types";
import {
  Badge,
  NextButton,
  OfficialObjective,
  PageHeading,
  TechnicalDetails,
} from "./shared";
export function Review({
  reviews,
  update,
  next,
}: {
  reviews: Record<string, LocalReview>;
  update: (id: string, value: LocalReview) => void;
  next: () => void;
}) {
  const [active, setActive] = useState("symbols");
  const [editing, setEditing] = useState(false);
  const item = demo.reviewQueue.find((c) => c.id === active)!;
  const state = reviews[active];
  const revised =
    state.name !== item.name ||
    state.domain !== item.domain ||
    state.description !== item.description;
  const settled = Object.values(reviews).filter(
    (r) => r.status !== "Awaiting demo review",
  ).length;
  return (
    <>
      <PageHeading
        eyebrow="04 / ACADEMIC REVIEW WORKSPACE"
        title="Human Review"
      >
        AI handles the repetitive mapping work. Academic experts review the
        decisions that shape the curriculum model.
      </PageHeading>
      <div className="demo-notice">
        <ShieldCheck size={20} />
        <div>
          <strong>Demo Review Queue</strong>
          <p>
            Replay {demo.reviewQueue.length} real examples already approved in
            the audit history. Your actions are temporary and do not change the
            official graph.
          </p>
        </div>
        <Badge>
          {settled} / {demo.reviewQueue.length} reviewed
        </Badge>
      </div>
      <div className="review-layout">
        <nav className="review-queue" aria-label="Review cases">
          <div className="section-label">EXAMPLE REVIEW ITEMS</div>
          {demo.reviewQueue.map((c, i) => (
            <button
              key={c.id}
              className={`queue-card ${active === c.id ? "selected" : ""}`}
              onClick={() => setActive(c.id)}
            >
              <span className="queue-number">
                0{i + 1} / {c.kind}
              </span>
              <strong>{c.name}</strong>
              <span className="queue-context">
                {c.objectives.map((o) => `${o.tier} ${o.code}`).join(" + ")}
              </span>
              <Badge
                tone={
                  reviews[c.id].status === "Rejected"
                    ? "red"
                    : reviews[c.id].status === "Awaiting demo review"
                      ? "amber"
                      : "green"
                }
              >
                {reviews[c.id].status}
              </Badge>
            </button>
          ))}
          <p className="queue-help">
            Review the evidence.
            <br />
            Shape the academic model.
          </p>
        </nav>
        <section className="panel review-detail" aria-label={item.kind}>
          <div className="section-heading">
            <div>
              <div className="eyebrow">{item.kind}</div>
              <h2>
                {active === "regions"
                  ? "One skill. Different scope."
                  : "A distinct skill in mathematical notation."}
              </h2>
            </div>
            <Badge
              tone={
                state.status === "Rejected"
                  ? "red"
                  : state.status === "Awaiting demo review"
                    ? "amber"
                    : "green"
              }
            >
              {state.status}
            </Badge>
          </div>
          <div className="section-label mt-7">
            OFFICIAL OBJECTIVE{item.objectives.length > 1 ? "S" : ""}
          </div>
          <div className={item.objectives.length > 1 ? "scope-columns" : ""}>
            {item.objectives.map((o) => (
              <div key={o.id}>
                <OfficialObjective objective={o} />
                {active === "regions" && (
                  <div className="scope-tag">
                    <span>SYLLABUS SCOPE</span>
                    <strong>
                      {o.scope?.constraints.join(" · ") ||
                        "Scope not specified"}
                    </strong>
                  </div>
                )}
              </div>
            ))}
          </div>
          {active === "regions" && (
            <div className="consolidation-bridge">
              <ArrowDown size={20} />
              <strong>Same underlying competency</strong>
              <span>Different syllabus scope — not a new academic skill</span>
            </div>
          )}
          <div className="recommendation">
            <div className="flex justify-between items-center gap-3">
              <span className="section-label">
                {revised ? "YOUR DEMO REVISION" : "AI RECOMMENDATION"}
              </span>
              <Badge tone="teal">
                {Math.round(item.confidence * 100)}% AI confidence
              </Badge>
            </div>
            <h3>{state.name}</h3>
            <p>{state.description}</p>
            <div className="recommendation-meta">
              <span>
                Subject domain <strong>{state.domain}</strong>
              </span>
              <span>
                Relationship{" "}
                <strong>
                  {item.relationship === "merge"
                    ? "Consolidate into one skill"
                    : "Equivalent"}
                </strong>
              </span>
            </div>
            <small>
              Domain source:{" "}
              {revised ? "Local demo revision" : item.domainSource}
            </small>
          </div>
          <div className="reasoning">
            <h3>Why this recommendation?</h3>
            <p>{item.reasoning}</p>
            <small>
              Confidence is the model’s estimate for this suggestion, not a
              measured accuracy score.
            </small>
          </div>
          <TechnicalDetails>
            <p>Canonical ID: {item.canonicalId}</p>
            {item.objectives.map((o) => (
              <p key={o.id}>Official source ID: {o.id}</p>
            ))}
            <p>
              Proposal status: {item.sourceStatus} · Confidence:{" "}
              {item.confidence} · Relationship: {item.relationship}
            </p>
            <p>
              Historical decision: {item.historicalDecisionId} ·{" "}
              {item.historicalStatus}
            </p>
            <p>Human reviewer notes: {item.reviewerNotes}</p>
          </TechnicalDetails>
          <div className="review-actions">
            <span role="status">
              {state.status === "Awaiting demo review"
                ? "Your academic judgement matters."
                : `${state.status} · local demo only`}
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                className="reject-button"
                onClick={() => update(active, { ...state, status: "Rejected" })}
              >
                <X size={16} />
                Reject
              </button>
              <button className="secondary" onClick={() => setEditing(true)}>
                <Pencil size={15} />
                Modify
              </button>
              <button
                className="primary"
                onClick={() => update(active, { ...state, status: "Approved" })}
              >
                <Check size={16} />
                Approve
              </button>
            </div>
          </div>
        </section>
      </div>
      <div className="page-action">
        <p>
          Approved decisions become the foundation of a shared academic graph.
        </p>
        <NextButton onClick={next}>View Approved Graph</NextButton>
      </div>
      {editing && (
        <ModifyDialog
          item={item}
          value={state}
          close={() => setEditing(false)}
          save={(v) => {
            update(active, v);
            setEditing(false);
          }}
        />
      )}
    </>
  );
}
function ModifyDialog({
  item,
  value,
  close,
  save,
}: {
  item: ReviewCase;
  value: LocalReview;
  close: () => void;
  save: (v: LocalReview) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState(value.name);
  const [domain, setDomain] = useState(value.domain);
  const [description, setDescription] = useState(value.description);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modify-dialog"
      aria-labelledby="modify-title"
      onCancel={close}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim() && domain.trim() && description.trim())
            save({
              name: name.trim(),
              domain: domain.trim(),
              description: description.trim(),
              status: "Modified",
            });
        }}
      >
        <div className="section-heading">
          <h2 id="modify-title">Modify academic skill</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Close modification"
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <p>
          Refine this example for the demo. The official decision history
          remains unchanged.
        </p>
        <label>
          Skill Name
          <input
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Subject Domain
          <input
            required
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          />
        </label>
        <label htmlFor="skill-description">Description</label>
        <textarea
          id="skill-description"
          required
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <p className="muted text-sm">{item.kind} · Local demo only</p>
        <div className="dialog-actions">
          <button className="secondary" type="button" onClick={close}>
            Cancel
          </button>
          <button
            className="primary"
            type="submit"
            disabled={!name.trim() || !domain.trim() || !description.trim()}
          >
            Save demo changes
          </button>
        </div>
      </form>
    </dialog>
  );
}
