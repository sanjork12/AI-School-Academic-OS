import { ArrowRight, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";
import type { ObjectiveView } from "@/data/types";
import { demo } from "@/data/demo";
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}
export function NextButton({
  children,
  onClick,
  disabled = false,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button className="primary" onClick={onClick} disabled={disabled}>
      {children}
      <ArrowRight size={17} />
    </button>
  );
}
export function Metrics() {
  const s = demo.processingSummary;
  return (
    <div className="metrics">
      {[
        [s.official, "Official objectives"],
        [s.skills, "Academic skills"],
        [s.mappings, "Approved mappings"],
        [s.unmapped, "Unmapped objectives"],
      ].map(([value, label]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}
export function TechnicalDetails({ children }: { children: ReactNode }) {
  return (
    <details className="technical">
      <summary>Technical details</summary>
      <div>{children}</div>
    </details>
  );
}
export function OfficialObjective({
  objective: o,
  showMapping = false,
}: {
  objective: ObjectiveView;
  showMapping?: boolean;
}) {
  return (
    <article className="objective">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge>{o.tier}</Badge>
          <span className="objective-code">{o.code}</span>
        </div>
        {showMapping && (
          <Badge tone={o.mappings.length ? "green" : "amber"}>
            {o.mappings.length ? "Mapped · approved" : "Unmapped"}
          </Badge>
        )}
      </div>
      <p className="official-wording">{o.wording}</p>
      {o.formattingWarning && (
        <p className="source-warning">
          <Info size={15} />
          Source formatting requires verification. Original wording preserved.
        </p>
      )}
      {showMapping &&
        o.mappings.map((m) => (
          <div className="mapping-label" key={m.id}>
            <CheckCircle2 size={16} />
            <span>{m.name}</span>
          </div>
        ))}
      {showMapping && (
        <TechnicalDetails>
          <p>Official source ID: {o.id}</p>
          {o.mappings.length ? (
            o.mappings.map((m) => (
              <div key={m.id}>
                <p>Canonical ID: {m.id}</p>
                <p>
                  Relationship: {m.relationship} · Confidence: {m.confidence} ·
                  Status: {m.status}
                </p>
              </div>
            ))
          ) : (
            <p>No approved mapping in this snapshot.</p>
          )}
        </TechnicalDetails>
      )}
    </article>
  );
}
