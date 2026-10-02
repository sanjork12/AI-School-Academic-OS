"""Read-only v0.2 validation; real references are checked against local v0.1 sources."""

import argparse
import json
from pathlib import Path

from academic_knowledge_schema_v02 import AcademicKnowledgePrototype

ROOT = Path(__file__).resolve().parent
DEFAULT_FILE = ROOT / "output/academic_knowledge_v02_prototype.json"
AUTHORITY_BY_SOURCE = {
    "official_syllabus": "official_requirement",
    "official_specification_note": "official_requirement",
    "official_teacher_guide": "official_clarification",
    "official_past_paper": "official_assessment",
    "official_mark_scheme": "official_assessment",
    "official_or_endorsed_textbook": "official_or_endorsed_textbook",
    "third_party_textbook": "third_party_material",
    "other": "unclassified",
}


def load_real_sources(root=ROOT):
    """Explicit allowlist: do not discover files or load environment settings."""
    def read(name):
        return json.loads((root / "output" / name).read_text(encoding="utf-8"))

    curricula = {}
    objectives = {}
    for name in ("topic2_foundation_parsed.json", "topic2_higher_parsed.json"):
        data = read(name)
        source = f"output/{name}"
        curricula[source] = data
        for subtopic in data["subtopics"]:
            for objective in subtopic["objectives"]:
                source_id = objective["source_id"]
                if source_id in objectives:
                    raise ValueError(f"Duplicate official source ID in v0.1: {source_id}")
                objectives[source_id] = (source, data, objective)
    return {
        "curricula": curricula, "objectives": objectives,
        "graph": read("topic2_canonical_promoted.json"),
        "scopes": read("topic2_scope_metadata_prototype.json")["metadata"],
        "decisions": read("topic2_human_review_decisions.json")["decisions"],
    }


def _index(records, key, label):
    indexed = {}
    for record in records:
        value = key(record)
        if value in indexed:
            raise ValueError(f"Duplicate {label}: {value}")
        indexed[value] = record
    return indexed


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_document(data, sources=None):
    # Revalidate even an already-constructed model; model_copy must not bypass checks.
    if isinstance(data, AcademicKnowledgePrototype):
        data = data.model_dump()
    model = AcademicKnowledgePrototype.model_validate(data)
    sources = load_real_sources() if sources is None else sources
    contexts = _index(model.contexts, lambda r: r.context_id, "context ID")
    canonical = _index(model.competencies, lambda r: r.canonical_id, "canonical ID")
    objectives = _index(model.objective_references,
                        lambda r: (r.official_source_id, r.context_id), "objective/context pair")
    scopes = _index(model.scopes, lambda r: r.scope_id, "scope ID")
    evidence = _index(model.evidence, lambda r: r.evidence_id, "evidence ID")
    _index(model.mappings, lambda r: (r.official_source_id, r.context_id, r.canonical_id),
           "mapping triple")
    questions = _index(model.questions, lambda r: r.question_id, "question ID")
    _index(model.question_mappings, lambda r: (r.question_id, r.canonical_id), "question mapping")
    _index(model.question_difficulties, lambda r: r.question_id, "question difficulty")
    real_nodes = {r["canonical_id"]: r for r in sources["graph"]["canonical_objectives"]}
    real_mappings = {(r["official_source_id"], r["canonical_id"]): r
                     for r in sources["graph"]["mappings"]}
    real_scopes = {(r["official_source_id"], r["canonical_id"]): r for r in sources["scopes"]}
    real_decisions = {r["decision_id"]: r for r in sources["decisions"]}

    for c in model.contexts:
        if c.provenance.origin == "synthetic":
            _require(c.context_id.startswith("SYN-"), "Synthetic context ID must start SYN-")
        else:
            source = sources["curricula"].get(c.provenance.source_reference)
            _require(source is not None, f"Unverified real context: {c.context_id}")
            for field in ("exam_board", "qualification", "subject", "specification_code"):
                _require(getattr(c, field) == source[field], f"Real context {field} mismatch")
            _require(c.tier == source["tier_source"], "Real context tier mismatch")
            for field in ("curriculum_version", "educational_stage", "pathway"):
                _require(getattr(c, field) == source.get(field), f"Unverified real context {field}")

    for c in model.competencies:
        if c.provenance.origin == "real":
            original = real_nodes.get(c.canonical_id)
            _require(original is not None, f"Unverified real canonical ID: {c.canonical_id}")
            for field in ("subject_domain", "skill_name", "description", "status"):
                _require(getattr(c, field) == original.get(field), f"Real competency {field} mismatch")
            _require(c.provenance.source_reference ==
                     f"output/topic2_canonical_promoted.json#{c.canonical_id}",
                     "Real competency source reference mismatch")
        else:
            _require(c.canonical_id not in real_nodes, "Real canonical record marked synthetic")

    for o in model.objective_references:
        _require(o.context_id in contexts, f"Unknown context: {o.context_id}")
        ctx = contexts[o.context_id]
        _require(o.provenance.origin == ctx.provenance.origin, "Objective/context origin mismatch")
        original = sources["objectives"].get(o.official_source_id)
        if o.provenance.origin == "real":
            _require(original is not None, f"Unknown real official ID: {o.official_source_id}")
            source, _, objective = original
            _require(ctx.provenance.source_reference == source, "Wrong context for official objective")
            _require(o.provenance.source_reference == f"{source}#{o.official_source_id}",
                     "Official objective source reference mismatch")
            _require(o.wording_excerpt is None or o.wording_excerpt == objective["official_text"],
                     "Real official wording must match parsed source exactly")
        else:
            _require(original is None, "Real official objective marked synthetic")
            _require(o.official_source_id.startswith("SYN-"), "Synthetic objective ID must start SYN-")

    def target(record):
        key = (record.official_source_id, record.context_id)
        _require(key in objectives, f"Unknown objective/context reference: {key}")
        _require(record.provenance.origin == objectives[key].provenance.origin,
                 "Record/objective origin mismatch")
        if record.canonical_id is not None:
            _require(record.canonical_id in canonical, f"Unknown canonical reference: {record.canonical_id}")

    def attached(ids, record):
        _require(len(ids) == len(set(ids)), "Duplicate evidence reference")
        result = []
        for identifier in ids:
            _require(identifier in evidence, f"Unknown evidence reference: {identifier}")
            e = evidence[identifier]
            _require((e.official_source_id, e.context_id) ==
                     (record.official_source_id, record.context_id), "Evidence objective/context mismatch")
            _require(e.canonical_id is None or e.canonical_id == record.canonical_id,
                     "Evidence canonical target mismatch")
            if e.scope_id is not None:
                _require(e.scope_id in scopes, f"Unknown evidence scope: {e.scope_id}")
                s = scopes[e.scope_id]
                _require(s.canonical_id == record.canonical_id, "Evidence scope canonical mismatch")
                if hasattr(record, "scope_id"):
                    _require(record.scope_id == e.scope_id, "Evidence scope target mismatch")
            result.append(e)
        return result

    for e in model.evidence:
        target(e)
        _require(e.authority == AUTHORITY_BY_SOURCE[e.source_type], "Evidence authority/source mismatch")
        if e.scope_id is not None:
            _require(e.scope_id in scopes, f"Unknown scope reference: {e.scope_id}")
            s = scopes[e.scope_id]
            _require((e.official_source_id, e.context_id) == (s.official_source_id, s.context_id),
                     "Evidence/scope objective mismatch")
            _require(e.canonical_id is None or e.canonical_id == s.canonical_id,
                     "Evidence/scope canonical mismatch")
        if e.provenance.origin == "real":
            source, _, objective = sources["objectives"][e.official_source_id]
            # v0.2 prototype has verified parsed syllabus sources only. No fake paper imports.
            _require(e.source_type == "official_syllabus" and
                     e.provenance.source_reference == f"{source}#{e.official_source_id}",
                     "Unverified real evidence source")
            _require(e.observation == objective["official_text"], "Real evidence quote differs from source")

    for s in model.scopes:
        target(s)
        attached(s.evidence_ids, s)
        excluded = [x.application for x in s.excluded_applications]
        _require(len(excluded) == len(set(excluded)), "Duplicate excluded application")
        _require(not set(excluded) & (set(s.included_applications) | set(s.unresolved_scope)),
                 "Application cannot be excluded and included/unresolved")
        for exclusion in s.excluded_applications:
            supporting = attached(exclusion.evidence_ids, s)
            _require(exclusion.review_status == "approved", "Exclusion requires explicit human review")
            _require(any(
                e.explicit_exclusion and e.application == exclusion.application
                and e.scope_id == s.scope_id and e.canonical_id == s.canonical_id
                and e.observation_status == "observed" and e.evidence_role == "supports"
                and e.review_status == "approved"
                and e.source_type in ("official_syllabus", "official_specification_note", "official_teacher_guide")
                for e in supporting
            ), "Exclusion needs reviewed explicit official evidence; NOT OBSERVED is not EXCLUDED")
        if s.provenance.origin == "real":
            original = real_scopes.get((s.official_source_id, s.canonical_id))
            _require(original is not None, "Unverified real scope")
            for field in ("scope_description", "constraints", "review_status"):
                _require(getattr(s, field) == original[field], f"Real scope {field} mismatch")
            _require(s.provenance.source_reference ==
                     f"output/topic2_scope_metadata_prototype.json#{s.official_source_id}/{s.canonical_id}",
                     "Real scope source mismatch")
            _require(not s.included_applications and not s.excluded_applications,
                     "Do not invent real scope applications in this read-only prototype")

    for m in model.mappings:
        target(m)
        attached(m.evidence_ids, m)
        if m.provenance.origin == "real":
            original = real_mappings.get((m.official_source_id, m.canonical_id))
            _require(original is not None, "Unverified real mapping")
            for field in ("relationship", "confidence", "mapping_method", "review_status"):
                _require(getattr(m, field) == original[field], f"Real mapping {field} mismatch")
            _require(m.provenance.source_reference ==
                     f"output/topic2_canonical_promoted.json#{m.official_source_id}/{m.canonical_id}",
                     "Real mapping source mismatch")
        if m.human_review_decision_id is not None:
            d = real_decisions.get(m.human_review_decision_id)
            _require(d is not None and m.provenance.origin == "real", "Invalid human decision reference")
            _require(d["decision"] == "approve" and d["approved_canonical_id"] == m.canonical_id,
                     "Human decision canonical mismatch")
            _require(any(x["official_source_id"] == m.official_source_id and
                         x["canonical_id"] == m.canonical_id for x in d["approved_official_mappings"]),
                     "Human decision does not approve this mapping")

    for q in model.questions:
        # No real assessment corpus has been imported or verified for this prototype.
        _require(q.provenance.origin == "synthetic" and q.question_id.startswith("SYN-"),
                 "Only explicitly synthetic questions are registered in this prototype")
        if q.curriculum_context_id is not None:
            _require(q.curriculum_context_id in contexts, "Unknown question context reference")
    for m in model.question_mappings:
        _require(m.question_id in questions, "Unknown question reference")
        _require(m.canonical_id in canonical, "Unknown question canonical reference")
    for d in model.question_difficulties:
        _require(d.question_id in questions, "Unknown difficulty question reference")
        _require(d.provenance.origin == questions[d.question_id].provenance.origin,
                 "Difficulty/question origin mismatch")
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_FILE)
    args = parser.parse_args()
    try:
        model = validate_document(json.loads(args.input.read_text(encoding="utf-8")))
    except (ValueError, OSError) as error:
        print(f"V0.2 VALIDATION FAILED: {error}")
        return 1
    for field in ("contexts", "competencies", "objective_references", "scopes", "evidence",
                  "mappings", "questions", "question_mappings", "question_difficulties"):
        print(f"{field}: {len(getattr(model, field))}")
    print("Errors: 0\nV0.2 STRUCTURE AND PROVENANCE VALIDATION PASSED")
    print("Academic interpretations and synthetic difficulty values are not production approvals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
