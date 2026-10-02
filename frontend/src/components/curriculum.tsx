"use client";
import { useState } from "react";
import { BookOpen, ArrowUpRight } from "lucide-react";
import { demo } from "@/data/demo";
import type { Tier } from "@/data/types";
import {
  Badge,
  Metrics,
  NextButton,
  OfficialObjective,
  PageHeading,
} from "./shared";
export function Curriculum({ next }: { next: () => void }) {
  const [code, setCode] = useState("2.8");
  const [tier, setTier] = useState<Tier>("Foundation");
  const topic = demo.topics.find((t) => t.code === code)!;
  const content = topic.tiers.find((t) => t.tier === tier)!;
  return (
    <>
      <PageHeading
        eyebrow="03 / CURRICULUM EXPLORER"
        title={`Topic ${demo.curriculum.topicCode} · ${demo.curriculum.topicName}`}
      >
        The official curriculum, organised into objectives and connected to
        approved academic skills.
      </PageHeading>
      <Metrics />
      <div className="explorer">
        <nav className="panel curriculum-tree" aria-label="Subtopics">
          <div className="section-label">
            TOPIC {demo.curriculum.topicCode} / SUBTOPICS
          </div>
          {demo.topics.map((t) => (
            <button
              key={t.code}
              className={t.code === code ? "selected" : ""}
              aria-current={t.code === code ? "true" : undefined}
              onClick={() => setCode(t.code)}
            >
              <span>{t.code}</span>
              <strong>{t.name}</strong>
              {t.code === "2.8" && <ArrowUpRight size={15} />}
            </button>
          ))}
          <div className="tree-foot">
            <BookOpen size={17} />
            <span>
              Official wording is preserved.
              <br />
              Academic interpretation is separate.
            </span>
          </div>
        </nav>
        <section className="objectives-pane">
          <div className="section-heading">
            <div>
              <div className="eyebrow">OFFICIAL OBJECTIVES</div>
              <h2>
                {topic.code} {topic.name}
              </h2>
            </div>
            <div className="tier-toggle" aria-label="Tier">
              {(["Foundation", "Higher"] as Tier[]).map((t) => (
                <button
                  key={t}
                  aria-pressed={tier === t}
                  className={tier === t ? "active" : ""}
                  onClick={() => setTier(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 mb-5">
            <Badge>{content.objectives.length} objectives</Badge>
            <span className="muted text-sm">
              {tier} source · {demo.curriculum.specification}
            </span>
          </div>
          {content.objectives.length ? (
            content.objectives.map((o) => (
              <OfficialObjective key={o.id} objective={o} showMapping />
            ))
          ) : (
            <div className="panel empty">
              <BookOpen />
              <h3>No separate objectives in this tier</h3>
              <p>Read the source context below, or switch tiers.</p>
            </div>
          )}
          {content.notes.length > 0 && (
            <details className="source-notes">
              <summary>Subtopic source notes · context only</summary>
              <p className="muted text-sm">
                These notes do not expand individual objective requirements.
                Extracted mathematical formatting is preserved and may need
                verification.
              </p>
              <ul>
                {content.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      </div>
      <div className="page-action">
        <p>Next: see how an expert reviews a mapping and a scope difference.</p>
        <NextButton onClick={next}>Open Human Review</NextButton>
      </div>
    </>
  );
}
