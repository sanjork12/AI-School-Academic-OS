// Read only these public curriculum artifacts; never scan the project or load .env.
import { readFile, writeFile } from "node:fs/promises";
const sources = [
  "topic2_foundation_parsed.json",
  "topic2_higher_parsed.json",
  "topic2_ai_mapping_proposals.json",
  "topic2_ai_consolidation_proposals.json",
  "topic2_scope_metadata_prototype.json",
  "topic2_human_review_decisions.json",
  "topic2_canonical_prototype.json",
  "topic2_canonical_promoted.json",
];
const [
  foundation,
  higher,
  mappingsAI,
  consolidationAI,
  scope,
  history,
  baseline,
  graph,
] = await Promise.all(
  sources.map(async (name) =>
    JSON.parse(
      await readFile(new URL(`../../output/${name}`, import.meta.url), "utf8"),
    ),
  ),
);
if (!baseline.canonical_objectives || !graph.canonical_objectives)
  throw new Error("Missing canonical snapshot");
const approved = graph.mappings.filter((m) => m.review_status === "approved");
const nodes = graph.canonical_objectives.filter((n) => n.status === "approved");
const nodeById = new Map(nodes.map((n) => [n.canonical_id, n]));
const objectiveById = new Map();
const topics = foundation.subtopics.map((subtopic) => ({
  code: subtopic.code,
  name: subtopic.name,
  tiers: [foundation, higher].map((curriculum) => {
    const sub = curriculum.subtopics.find((s) => s.code === subtopic.code);
    if (!sub) throw new Error(`Missing subtopic ${subtopic.code}`);
    return {
      tier: curriculum.tier_source,
      notes: sub.notes,
      objectives: sub.objectives.map((o) => {
        const metadata = scope.metadata.find(
          (s) =>
            s.official_source_id === o.source_id &&
            s.review_status === "approved",
        );
        const view = {
          id: o.source_id,
          code: `${sub.code}${o.code}`,
          wording: o.official_text,
          tier: curriculum.tier_source,
          formattingWarning: /[\uE000-\uF8FF\uFFFD]/u.test(o.official_text),
          mappings: approved
            .filter((m) => m.official_source_id === o.source_id)
            .map((m) => {
              const node = nodeById.get(m.canonical_id);
              if (!node) throw new Error(`Missing node ${m.canonical_id}`);
              return {
                id: node.canonical_id,
                name: node.skill_name,
                relationship: m.relationship,
                confidence: m.confidence,
                status: m.review_status,
              };
            }),
          scope: metadata
            ? {
                description: metadata.scope_description,
                constraints: metadata.constraints,
              }
            : null,
        };
        if (objectiveById.has(view.id))
          throw new Error(`Duplicate source ${view.id}`);
        objectiveById.set(view.id, view);
        return view;
      }),
    };
  }),
}));
const cases = [
  {
    id: "symbols",
    decisionId: "REV-4MA1-T2-INEQ-SYMBOLS-001",
    proposal: mappingsAI.proposals.find(
      (p) => p.official_source_id === "EDX-4MA1-F-2.8-A",
    ),
    kind: "Curriculum mapping",
  },
  {
    id: "regions",
    decisionId: "REV-4MA1-T2-INEQ-REGION-001",
    proposal: consolidationAI.proposals.find(
      (p) => p.recommended_canonical_id === "CAN-ALG-INEQ-REGION-INTERPRET",
    ),
    kind: "Skill consolidation",
  },
];
const reviewQueue = cases.map(({ id, decisionId, proposal: p, kind }) => {
  const d = history.decisions.find((d) => d.decision_id === decisionId);
  if (!p || !d) throw new Error(`Missing review evidence: ${decisionId}`);
  return {
    id,
    kind,
    name: p.proposed_skill_name ?? p.skill_name,
    domain: p.proposed_subject_domain ?? d.approved_subject_domain,
    domainSource: p.proposed_subject_domain
      ? "AI proposal"
      : "Historical human review (legacy proposal has no domain)",
    description: p.proposed_description ?? p.description,
    canonicalId: p.proposed_canonical_id ?? p.recommended_canonical_id,
    reasoning: p.reasoning,
    confidence: p.confidence,
    relationship: p.relationship ?? "merge",
    sourceStatus: p.review_status,
    historicalDecisionId: d.decision_id,
    historicalStatus: d.decision,
    reviewerNotes: d.reviewer_notes,
    objectives: d.approved_official_mappings.map((m) => {
      const o = objectiveById.get(m.official_source_id);
      if (!o) throw new Error("Missing review objective");
      return o;
    }),
  };
});
const mapped = new Set(approved.map((m) => m.official_source_id));
for (const id of mapped)
  if (!objectiveById.has(id)) throw new Error(`Unknown source ${id}`);
const output = {
  curriculum: {
    examBoard: foundation.exam_board,
    qualification: foundation.qualification,
    subject: foundation.subject,
    specification: foundation.specification_code,
    topicCode: foundation.topic_code,
    topicName: foundation.topic_name,
    warnings: [...foundation.warnings, ...higher.warnings],
  },
  processingSummary: {
    official: objectiveById.size,
    skills: nodes.length,
    mappings: approved.length,
    mapped: mapped.size,
    unmapped: objectiveById.size - mapped.size,
    decisions: history.decisions.length,
    approvedDecisions: history.decisions.filter((d) => d.decision === "approve")
      .length,
    mappingProposals: mappingsAI.proposals.length,
    consolidationProposals: consolidationAI.proposals.length,
  },
  topics,
  reviewQueue,
  approvedGraph: nodes.map((n) => ({
    id: n.canonical_id,
    name: n.skill_name,
    domain: n.subject_domain,
    description: n.description,
    objectives: approved
      .filter((m) => m.canonical_id === n.canonical_id)
      .map((m) => objectiveById.get(m.official_source_id)),
  })),
  provenance: {
    sources: sources.map((s) => `output/${s}`),
    note: "Derived presentation data. Not an audit log. Legacy scope difficulty_level is intentionally excluded.",
  },
};
await writeFile(
  new URL("../src/data/demo.json", import.meta.url),
  JSON.stringify(output, null, 2) + "\n",
  "utf8",
);
console.log("Prepared static demo:", output.processingSummary);
