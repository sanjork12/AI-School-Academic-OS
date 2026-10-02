export type Tier = "Foundation" | "Higher";
export interface MappingView {
  id: string;
  name: string;
  relationship: string;
  confidence: number;
  status: string;
}
export interface ObjectiveView {
  id: string;
  code: string;
  wording: string;
  tier: Tier;
  formattingWarning: boolean;
  mappings: MappingView[];
  scope: { description: string; constraints: string[] } | null;
}
export interface TopicView {
  code: string;
  name: string;
  tiers: { tier: Tier; notes: string[]; objectives: ObjectiveView[] }[];
}
export interface ReviewCase {
  id: string;
  kind: string;
  name: string;
  domain: string;
  domainSource: string;
  description: string;
  canonicalId: string;
  reasoning: string;
  confidence: number;
  relationship: string;
  sourceStatus: string;
  historicalDecisionId: string;
  historicalStatus: string;
  reviewerNotes: string;
  objectives: ObjectiveView[];
}
export interface SkillView {
  id: string;
  name: string;
  domain: string;
  description: string;
  objectives: ObjectiveView[];
}
export interface CurriculumDemoView {
  curriculum: {
    examBoard: string;
    qualification: string;
    subject: string;
    specification: string;
    topicCode: string;
    topicName: string;
    warnings: string[];
  };
  processingSummary: {
    official: number;
    skills: number;
    mappings: number;
    mapped: number;
    unmapped: number;
    decisions: number;
    approvedDecisions: number;
    mappingProposals: number;
    consolidationProposals: number;
  };
  topics: TopicView[];
  reviewQueue: ReviewCase[];
  approvedGraph: SkillView[];
  provenance: { sources: string[]; note: string };
}
export type ReviewStatus =
  "Awaiting demo review" | "Approved" | "Modified" | "Rejected";
export interface LocalReview {
  status: ReviewStatus;
  name: string;
  domain: string;
  description: string;
}
