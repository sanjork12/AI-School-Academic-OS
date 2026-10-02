"""Read-only structural and source-readiness checks. Trust never comes from the input JSON."""
import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from academic_knowledge_schema_v03 import AcademicKnowledgePrototype, Reviewable, TargetRef

ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "output/academic_knowledge_v03/prototype.json"
OFFICIAL_SCOPE = {"official_syllabus", "official_specification_note", "official_teacher_guide"}
ASSESSMENT = {"official_past_paper", "official_mark_scheme"}


def digest(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def content_digest(record):
    """Bind decisions to academic content, excluding review pointers even in nested records."""
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in
                    {"review_status", "review_decision_id", "registry_decision_id"}}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    return digest(clean(record.model_dump() if hasattr(record, "model_dump") else record))


@dataclass(frozen=True)
class SourceVerification:
    record_digest: str
    artifact_path: Path
    artifact_digest: str


@dataclass(frozen=True)
class LocatorVerification:
    record_digest: str
    source_content_digest: str
    verified_text: str | None = None


@dataclass
class ExternalTrust:
    """Caller-owned reviewed records. Never load these from the submitted model or arbitrary CLI JSON."""
    sources: dict[str, SourceVerification] = field(default_factory=dict)
    locators: dict[str, LocatorVerification] = field(default_factory=dict)
    decisions: dict[str, str] = field(default_factory=dict)  # decision_source_reference -> exact decision digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(records, key, label):
    result = {}
    for record in records:
        identifier = key(record)
        require(identifier not in result, f"Duplicate {label}: {identifier}")
        result[identifier] = record
    return result


def distinct(values, label):
    require(len(values) == len(set(values)), f"Duplicate {label}")


COLLECTIONS = {
    "context": ("contexts", "context_id"), "concept": ("concepts", "concept_id"),
    "competency": ("competencies", "canonical_id"), "concept_link": ("concept_links", "link_id"),
    "objective": ("objective_references", "objective_id"), "scope": ("scopes", "scope_id"),
    "objective_mapping": ("objective_mappings", "mapping_id"), "question": ("questions", "question_id"),
    "question_part": ("question_parts", "part_id"), "condition": ("task_conditions", "condition_id"),
    "resource": ("resources", "resource_id"), "resource_use": ("resource_uses", "use_id"),
    "part_mapping": ("part_mappings", "mapping_id"), "evidence": ("evidence", "evidence_id"),
}


class ValidationContext:
    def __init__(self, model, trust):
        self.model, self.trust = model, trust
        self.sources = index(model.sources, lambda r: r.source_id, "source")
        self.locators = index(model.locators, lambda r: r.locator_id, "locator")
        self.decisions = index(model.review_decisions, lambda r: r.decision_id, "decision")
        self.nodes = {kind: index(getattr(model, collection), lambda r, key=key: getattr(r, key), kind)
                      for kind, (collection, key) in COLLECTIONS.items()}
        self.nodes["action_classification"] = {c.canonical_id: c.action_classification
                                               for c in model.competencies if c.action_classification is not None}
        self.nodes["scope_exclusion"] = index([x for s in model.scopes for x in s.excluded_applications],
                                              lambda x: x.exclusion_id, "scope exclusion")

    def get(self, kind, identifier):
        require(identifier in self.nodes[kind], f"Unknown {kind}: {identifier}")
        return self.nodes[kind][identifier]

    def target(self, ref):
        return self.get(ref.kind, ref.id)

    def locator(self, identifier):
        require(identifier in self.locators, f"Unknown locator: {identifier}")
        return self.locators[identifier]

    def source(self, identifier):
        require(identifier in self.sources, f"Unknown source: {identifier}")
        return self.sources[identifier]

    def assessable(self, identifier):
        part = self.get("question_part", identifier)
        require(part.node_kind == "assessable", "Container cannot carry an assessment mapping/attachment/difficulty")
        return part

    def verified_locator(self, identifier):
        loc = self.locator(identifier)
        source = self.source(loc.source_id)
        return source.origin == "real" and source.verification_status == loc.verification_status == "verified"

    def attached(self, record, target):
        distinct(record.evidence_ids, "evidence references")
        records = []
        for identifier in record.evidence_ids:
            e = self.get("evidence", identifier)
            require(e.target == target, "Attached evidence target mismatch")
            require(e.provenance.origin == record.provenance.origin, "Evidence/record origin mismatch")
            records.append(e)
        return records

    def supporting(self, record, allowed_sources=None):
        for identifier in record.evidence_ids:
            e = self.get("evidence", identifier)
            source = self.source(self.locator(e.source_locator_ids[0]).source_id)
            if (e.evidence_role == "supports" and e.observation_status == "observed"
                    and e.review_status != "rejected" and e.provenance.origin == "real"
                    and all(self.verified_locator(x) for x in e.source_locator_ids)
                    and (allowed_sources is None or source.source_type in allowed_sources)):
                return True
        return False


def review_content_digest(data, target):
    """Bind a review to the claim AND the cited evidence/locations, not only mutable IDs."""
    model = data if isinstance(data, AcademicKnowledgePrototype) else AcademicKnowledgePrototype.model_validate(data)
    ctx = ValidationContext(model, ExternalTrust())
    target = TargetRef.model_validate(target) if isinstance(target, dict) else target
    record = ctx.target(target)
    evidence = [ctx.get("evidence", i) for i in getattr(record, "evidence_ids", [])]
    citations = evidence + ([record] if target.kind == "evidence" else [])
    locator_ids = sorted({i for e in citations for i in e.source_locator_ids})
    locators = [ctx.locator(i) for i in locator_ids]
    source_ids = sorted({l.source_id for l in locators})
    return digest({"record": content_digest(record),
                   "evidence": [(e.evidence_id, content_digest(e)) for e in evidence],
                   "locators": [(l.locator_id, digest(l)) for l in locators],
                   "sources": [(i, digest(ctx.source(i))) for i in source_ids]})


def _validate(data, trust):
    if hasattr(data, "model_dump"):
        data = data.model_dump()  # model_copy cannot bypass validation
    model = AcademicKnowledgePrototype.model_validate(data)
    ctx = ValidationContext(model, trust)

    for s in model.sources:
        if s.verification_status == "verified":
            trusted = trust.sources.get(s.verification_reference)
            require(trusted is not None and trusted.record_digest == digest(s), "Untrusted source verification")
            require(str(trusted.artifact_path) == s.artifact_reference, "Trusted artifact path mismatch")
            require(trusted.artifact_digest == s.content_digest, "Source digest differs from trusted record")
            require(hashlib.sha256(trusted.artifact_path.read_bytes()).hexdigest() == s.content_digest,
                    "Source artifact bytes changed")
    for loc in model.locators:
        source = ctx.source(loc.source_id)
        if loc.assessment_part_id is not None:
            part = ctx.get("question_part", loc.assessment_part_id)
            require(loc.assessment_question_id in (None, part.question_id), "Locator question/part mismatch")
        if loc.assessment_question_id is not None:
            ctx.get("question", loc.assessment_question_id)
        if loc.verification_status == "verified":
            trusted = trust.locators.get(loc.verification_reference)
            require(source.verification_status == "verified" and trusted is not None,
                    "Untrusted locator verification")
            require(trusted.record_digest == digest(loc) and trusted.source_content_digest == source.content_digest,
                    "Locator verification content mismatch")

    for kind, records in ctx.nodes.items():
        for record in records.values():
            if not hasattr(record, "provenance"):
                continue
            p = record.provenance
            distinct(p.source_references, "provenance reference")
            for reference in p.source_references:
                if reference.startswith("locator:"):
                    source = ctx.source(ctx.locator(reference[8:]).source_id)
                    require(not (p.origin == "real" and source.origin == "synthetic"),
                            "Real provenance cannot cite a synthetic source")
                else:
                    require(p.origin == "synthetic" and reference.startswith("synthetic://"),
                            "Provenance must reference a registered locator")

    index(model.concept_links, lambda r: (r.canonical_id, r.concept_id, r.relationship), "concept link pair")
    index(model.objective_mappings, lambda r: (r.objective_id, r.context_id, r.canonical_id), "objective mapping triple")
    index(model.part_mappings, lambda r: (r.part_id, r.canonical_id), "part competency pair")
    index(model.part_condition_links, lambda r: (r.part_id, r.condition_id), "part condition pair")
    index(model.resource_uses, lambda r: (r.resource_id, r.target.kind, r.target.id, r.relationship), "resource use")
    index(model.question_difficulties, lambda r: r.part_id, "part difficulty")
    index(model.gold_standard_entries, lambda r: r.entry_id, "Gold Standard entry")
    index([g for g in model.gold_standard_entries if g.target is not None],
          lambda r: (r.baseline_id, r.baseline_version, r.target.kind, r.target.id), "baseline target")

    for g in model.gold_standard_entries:
        decision_source = ctx.source(ctx.locator(g.decision_source_reference).source_id)
        require(decision_source.origin == g.provenance.origin, "Gold decision source origin mismatch")
        distinct(g.evidence_ids, "Gold evidence")
        for e in g.evidence_ids:
            ctx.get("evidence", e)
        if g.target is not None:
            ctx.target(g.target)
            require(g.target.kind == g.category, "Gold category/target mismatch")
        if g.disposition in ("approved", "strong_candidate", "candidate"):
            require(g.category == "competency", "Working competency status used on another category")
        if g.disposition != "deferred":
            require(g.target is not None or g.disposition == "recorded", "Active competency needs target")
        for reference in g.provenance.source_references:
            require(reference.startswith("locator:"), "Gold provenance needs registered locator")
            source = ctx.source(ctx.locator(reference[8:]).source_id)
            require(not (g.provenance.origin == "real" and source.origin == "synthetic"), "Gold provenance origin mismatch")

    for o in model.objective_references:
        ctx.get("context", o.context_id)
        loc = ctx.locator(o.source_locator_id)
        source = ctx.source(loc.source_id)
        require(source.source_type in OFFICIAL_SCOPE, "Objective needs a curriculum source")
        require(source.origin == o.provenance.origin, "Objective/source origin mismatch")
        if o.wording_excerpt is not None:
            require(ctx.verified_locator(loc.locator_id), "Official wording requires verified locator")
            text = trust.locators[loc.verification_reference].verified_text
            require(text is not None and o.wording_excerpt in text, "Official wording differs from verified text")
    for record in [*model.scopes, *model.objective_mappings]:
        obj = ctx.get("objective", record.objective_id)
        require(obj.context_id == record.context_id, "Objective/context mismatch")
        ctx.get("competency", record.canonical_id)
        require(obj.provenance.origin == record.provenance.origin, "Objective/record origin mismatch")
    for link in model.concept_links:
        ctx.get("competency", link.canonical_id)
        ctx.get("concept", link.concept_id)
    for resource in model.resources:
        if resource.artifact_source_id is not None:
            source = ctx.source(resource.artifact_source_id)
            require(source.origin == resource.provenance.origin, "Resource/source origin mismatch")

    for q in model.questions:
        source = ctx.source(q.paper_source_id)
        require(source.source_type in ("official_past_paper", "other"), "Question needs a question source")
        require(ctx.locator(q.source_locator_id).source_id == q.paper_source_id, "Question locator/source mismatch")
        require(ctx.locator(q.source_locator_id).assessment_question_id == q.question_id, "Question locator identity mismatch")
        require(source.origin == q.provenance.origin, "Question/source origin mismatch")
        if q.curriculum_context_id is not None:
            ctx.get("context", q.curriculum_context_id)
    for part in model.question_parts:
        q = ctx.get("question", part.question_id)
        loc = ctx.locator(part.source_locator_id)
        require(loc.source_id == q.paper_source_id and loc.assessment_part_id == part.part_id,
                "Part locator/source/identity mismatch")
        require(part.provenance.origin == q.provenance.origin, "Part/question origin mismatch")
        seen, node = {part.part_id}, part
        while node.parent_part_id is not None:
            parent = ctx.get("question_part", node.parent_part_id)
            require(parent.part_id not in seen, "Part parent cycle")
            require(parent.question_id == part.question_id, "Cross-question parent")
            require(parent.node_kind == "container", "Parent must be a container")
            seen.add(parent.part_id)
            node = parent
    for condition in model.task_conditions:
        q = ctx.get("question", condition.question_id)
        require(q.provenance.origin == condition.provenance.origin, "Condition/question origin mismatch")
        if condition.resource_id is not None:
            ctx.get("resource", condition.resource_id)
        require(condition.availability != "recalled_from_resource" or condition.resource_id is not None,
                "Recalled condition requires resource")
    for link in model.part_condition_links:
        part = ctx.assessable(link.part_id)
        condition = ctx.get("condition", link.condition_id)
        require(part.question_id == condition.question_id, "Cross-question condition attachment")
    for use in model.resource_uses:
        ctx.get("resource", use.resource_id)
        ctx.target(use.target)
        require((use.target.kind, use.relationship) in
                {("context", "familiarity_required"), ("question_part", "uses_context")},
                "Resource use relationship/target mismatch")
        if use.target.kind == "question_part":
            part = ctx.assessable(use.target.id)
            require(part.provenance.origin == use.provenance.origin, "Resource use/part origin mismatch")
    for mapping in model.part_mappings:
        part = ctx.assessable(mapping.part_id)
        ctx.get("competency", mapping.canonical_id)
        require(part.provenance.origin == mapping.provenance.origin, "Mapping/part origin mismatch")
        distinct(mapping.focus_concept_ids, "focus concepts")
        for identifier in mapping.focus_concept_ids:
            ctx.get("concept", identifier)
    for d in model.question_difficulties:
        part = ctx.assessable(d.part_id)
        require(d.provenance.origin == part.provenance.origin, "Difficulty/part origin mismatch")
        for ref in d.provenance.source_references:
            require(ref.startswith("locator:"), "Difficulty provenance requires locator")
            source = ctx.source(ctx.locator(ref[8:]).source_id)
            require(not (d.provenance.origin == "real" and source.origin == "synthetic"), "Difficulty provenance origin mismatch")

    for e in model.evidence:
        require(e.target.kind not in {"context", "objective", "evidence", "scope_exclusion", "action_classification"},
                "Invalid evidence target kind")
        target = ctx.target(e.target)
        distinct(e.source_locator_ids, "evidence locators")
        locs = [ctx.locator(x) for x in e.source_locator_ids]
        require(len({l.source_id for l in locs}) == 1, "One evidence record cannot mix source documents")
        source = ctx.source(locs[0].source_id)
        require(source.origin == e.provenance.origin, "Evidence/source origin mismatch")
        if e.context_id is not None:
            ctx.get("context", e.context_id)
        if e.objective_id is not None:
            obj = ctx.get("objective", e.objective_id)
            require(e.context_id is None or e.context_id == obj.context_id, "Evidence objective/context mismatch")
        if e.target.kind in {"scope", "objective_mapping"}:
            require(e.objective_id in (None, target.objective_id) and e.context_id in (None, target.context_id),
                    "Evidence curriculum target mismatch")
        if e.target.kind in {"part_mapping", "question_part"} and source.source_type in ASSESSMENT:
            part_id = target.part_id
            require(all(l.assessment_part_id == part_id for l in locs), "Assessment evidence part mismatch")
        if e.target.kind == "resource_use" and target.target.kind == "question_part" and source.source_type in ASSESSMENT:
            require(all(l.assessment_part_id == target.target.id for l in locs), "Resource evidence part mismatch")
        if e.target.kind in {"condition", "question"} and source.source_type in ASSESSMENT:
            question_id = target.question_id
            require(all((ctx.get("question_part", l.assessment_part_id).question_id if l.assessment_part_id
                         else l.assessment_question_id) == question_id for l in locs), "Task evidence question mismatch")
        if e.content_kind == "quotation":
            require(all(ctx.verified_locator(l.locator_id) for l in locs), "Quotation needs verified locators")
            texts = [trust.locators[l.verification_reference].verified_text for l in locs]
            require(any(t is not None and e.observation in t for t in texts), "Quotation differs from verified text")

    for kind, records in ctx.nodes.items():
        for identifier, record in records.items():
            if hasattr(record, "evidence_ids") and kind != "scope_exclusion":
                ctx.attached(record, TargetRef(kind=kind, id=identifier))

    superseded = set()
    for d in model.review_decisions:
        ctx.target(d.target)
        require(trust.decisions.get(d.decision_source_reference) == digest(d), "Untrusted human review decision")
        seen, node = {d.decision_id}, d
        while node.supersedes_decision_id is not None:
            require(node.supersedes_decision_id in ctx.decisions, "Unknown superseded decision")
            parent = ctx.decisions[node.supersedes_decision_id]
            require(parent.target == d.target, "Superseded decision target mismatch")
            require(parent.decision_id not in seen, "Review decision cycle")
            superseded.add(parent.decision_id)
            seen.add(parent.decision_id)
            node = parent

    index([d for d in model.review_decisions if d.decision_id not in superseded],
          lambda d: (d.target.kind, d.target.id), "active review target")

    def review(record, target, decision_id, status):
        if status == "pending":
            require(decision_id is None, "Pending record cannot reference an approval")
            return
        require(decision_id in ctx.decisions, "Reviewed record needs a trusted human decision")
        d = ctx.decisions[decision_id]
        require(d.target == target and d.decision == status, "Review decision target/status mismatch")
        require(d.decision_id not in superseded, "Superseded review cannot approve current record")
        require(d.target_content_digest == review_content_digest(model, target), "Stale review content digest")

    for kind, records in ctx.nodes.items():
        for identifier, record in records.items():
            if isinstance(record, Reviewable):
                review(record, TargetRef(kind=kind, id=identifier), record.review_decision_id, record.review_status)
                if record.review_status == "approved" and kind in {"part_mapping", "objective_mapping", "scope", "resource_use", "concept_link", "condition"}:
                    allowed = ASSESSMENT if kind == "part_mapping" else OFFICIAL_SCOPE if (
                        kind in {"scope", "objective_mapping"} or kind == "resource_use" and record.relationship == "familiarity_required"
                    ) else None
                    require(ctx.supporting(record, allowed), "Approved relation requires verified supporting evidence")
            if kind == "competency":
                if record.status == "draft":
                    require(record.registry_decision_id is None, "Draft competency cannot carry registry approval")
                else:
                    require(record.registry_decision_id in ctx.decisions, "Registry state requires trusted decision")
                    d = ctx.decisions[record.registry_decision_id]
                    require(record.status != "approved" or d.decision == "approved", "Registry approval mismatch")
                    review(record, TargetRef(kind=kind, id=identifier), record.registry_decision_id, d.decision)

    for scope in model.scopes:
        distinct(scope.concept_ids, "scope concepts")
        for c in scope.concept_ids:
            ctx.get("concept", c)
        excluded = [x.application for x in scope.excluded_applications]
        distinct(excluded, "excluded applications")
        require(not set(excluded) & (set(scope.included_applications) | set(scope.unresolved_scope)),
                "Excluded application is also included/unresolved")
        for x in scope.excluded_applications:
            require(x.review_status == "approved", "Exclusion needs explicit human approval")
            evs = ctx.attached(x, TargetRef(kind="scope", id=scope.scope_id))
            require(any(e.explicit_exclusion and e.application == x.application and e.review_status == "approved"
                        and e.observation_status == "observed" and e.evidence_role == "supports"
                        and ctx.source(ctx.locator(e.source_locator_ids[0]).source_id).source_type in OFFICIAL_SCOPE
                        and all(ctx.verified_locator(i) for i in e.source_locator_ids) for e in evs),
                    "Exclusion needs reviewed explicit official scope evidence; absence is not exclusion")
    return model, ctx


def validate_document(data, trust=None):
    return _validate(data, trust or ExternalTrust())[0]


def validation_report(data, selected_targets=None, trust=None):
    model, ctx = _validate(data, trust or ExternalTrust())
    targets = ([TargetRef(kind="part_mapping", id=m.mapping_id) for m in model.part_mappings]
               if selected_targets is None else [TargetRef.model_validate(t) if isinstance(t, dict) else t for t in selected_targets])
    distinct([(t.kind, t.id) for t in targets], "selected targets")
    results = []
    for target in targets:
        record = ctx.target(target)
        reasons = []
        evs = [ctx.get("evidence", x) for x in getattr(record, "evidence_ids", [])]
        if not evs:
            reasons.append("no_attached_evidence")
        if getattr(record, "provenance", None) is None or record.provenance.origin != "real":
            reasons.append("not_a_real_claim")
        for e in evs:
            if not all(ctx.verified_locator(x) for x in e.source_locator_ids):
                reasons.append(f"unverified_evidence:{e.evidence_id}")
        allowed = ASSESSMENT if target.kind == "part_mapping" else OFFICIAL_SCOPE if (
            target.kind in {"scope", "objective_mapping"} or target.kind == "resource_use" and record.relationship == "familiarity_required"
        ) else None
        if not hasattr(record, "evidence_ids") or not ctx.supporting(record, allowed):
            reasons.append("no_verified_supporting_source")
        results.append({"target": target.model_dump(), "source_verified": not reasons, "reasons": reasons,
                        "review_status": getattr(record, "review_status", None)})
    return {"structure_valid": True, "source_verified": bool(results) and all(r["source_verified"] for r in results),
            "selected_targets": results, "unverified_sources": [s.source_id for s in model.sources if s.verification_status != "verified"],
            "pending_review_count": sum(isinstance(r, Reviewable) and r.review_status == "pending"
                                        for records in ctx.nodes.values() for r in records.values()),
            "counts": {name: len(getattr(model, name)) for name in type(model).model_fields if isinstance(getattr(model, name), list)},
            "notice": "Structure and source readiness are not academic approval or production promotion."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--require-source-verified", action="store_true")
    args = parser.parse_args()
    try:
        report = validation_report(json.loads(args.input.read_text(encoding="utf-8")))
    except (ValueError, OSError) as error:
        print(json.dumps({"structure_valid": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if args.require_source_verified and not report["source_verified"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
