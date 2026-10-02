import {
  Network,
  ArrowDown,
  BookOpen,
  ClipboardCheck,
  ChartNoAxesCombined,
  GraduationCap,
  Waypoints,
  ShieldCheck,
} from "lucide-react";
import { demo } from "@/data/demo";
import type { LocalReview, SkillView } from "@/data/types";
import { Badge, Metrics, PageHeading, TechnicalDetails } from "./shared";
function SkillCard({ skill }: { skill: SkillView }) {
  return (
    <article className="panel graph-card">
      <div className="graph-node">
        <div className="flex items-center justify-between gap-2">
          <span className="section-label">ACADEMIC SKILL · {skill.domain}</span>
          <Badge tone="green">Approved</Badge>
        </div>
        <h2>{skill.name}</h2>
        <p>{skill.description}</p>
      </div>
      <div className="graph-connector">
        <ArrowDown size={22} />
        <span>Mapped to official objectives</span>
      </div>
      <div className="graph-leaves">
        {skill.objectives.map((o) => (
          <div className="graph-leaf" key={o.id}>
            <div className="flex gap-2 items-center">
              <Badge>{o.tier}</Badge>
              <strong>{o.code}</strong>
            </div>
            <p>{o.wording}</p>
            {o.formattingWarning && (
              <small className="source-warning">
                Source formatting requires verification
              </small>
            )}
            <div className="leaf-scope">
              <span>SCOPE</span>
              <strong>
                {o.scope
                  ? o.scope.constraints.join(" · ") || o.scope.description
                  : "As stated in the official objective"}
              </strong>
            </div>
          </div>
        ))}
      </div>
      <TechnicalDetails>
        <p>Canonical ID: {skill.id}</p>
        {skill.objectives.map((o) => (
          <p key={o.id}>Official source ID: {o.id}</p>
        ))}
      </TechnicalDetails>
    </article>
  );
}
export function ApprovedGraph({
  reviews,
}: {
  reviews: Record<string, LocalReview>;
}) {
  const featured = demo.reviewQueue.map((c) =>
    demo.approvedGraph.find((s) => s.id === c.canonicalId)!,
  );
  const remaining = demo.approvedGraph.filter((s) => !featured.includes(s));
  const acted = Object.entries(reviews).filter(
    ([, r]) => r.status !== "Awaiting demo review",
  );
  return (
    <>
      <PageHeading
        eyebrow="05 / A SHARED ACADEMIC FOUNDATION"
        title="Approved Academic Graph"
      >
        A trusted connection between what the syllabus requires and what
        students need to be able to do.
      </PageHeading>
      <div className="snapshot-label">
        <ShieldCheck size={17} />
        Official approved snapshot
        <span>Rebuilt from the baseline + complete human review history</span>
      </div>
      <Metrics />
      {acted.length > 0 && (
        <section className="demo-results">
          <div className="section-label">DEMO REVIEW RESULT · LOCAL ONLY</div>
          {acted.map(([id, r]) => (
            <p key={id}>
              <Badge tone={r.status === "Rejected" ? "red" : "green"}>
                {r.status}
              </Badge>
              <strong>{r.name}</strong>
              <span>{r.domain}</span>
            </p>
          ))}
          <small>
            These practice decisions do not alter the official snapshot below.
          </small>
        </section>
      )}
      <div className="section-heading graph-heading">
        <div>
          <h2>From syllabus wording to shared skills</h2>
          <p className="muted">
            Skill identity and tier scope remain separate.
          </p>
        </div>
        <Badge>{featured.length} featured connections</Badge>
      </div>
      <div className="featured-graphs">
        {[...featured].reverse().map((s) => (
          <SkillCard key={s.id} skill={s} />
        ))}
      </div>
      <details className="other-skills">
        <summary>
          Explore all {demo.processingSummary.skills} approved academic skills
        </summary>
        <div className="other-skills-grid">
          {remaining.map((s) => (
            <SkillCard key={s.id} skill={s} />
          ))}
        </div>
      </details>
      <section className="downstream">
        <div className="section-heading">
          <div>
            <div className="eyebrow">CONNECTED ACADEMIC INTELLIGENCE</div>
            <h2>Ready to power what comes next</h2>
          </div>
          <Badge>Future connected modules</Badge>
        </div>
        <p>
          A consistent academic graph can connect curriculum design to evidence
          of student learning.
        </p>
        <div className="downstream-grid">
          {[
            [BookOpen, "Question Bank"],
            [ClipboardCheck, "Assessment Generation"],
            [GraduationCap, "Student Mastery"],
            [ChartNoAxesCombined, "Academic Analytics"],
            [Waypoints, "Teaching Intervention"],
          ].map(([Icon, label]) => {
            const Component = Icon as typeof Network;
            return (
              <div key={label as string}>
                <Component size={24} />
                <strong>{label as string}</strong>
                <span>Next layer</span>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
