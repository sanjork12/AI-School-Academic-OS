"""Deterministic v0.3 working baseline. Never imports or runs the old promotion pipeline."""
import json
from pathlib import Path
from academic_knowledge_schema_v03 import AcademicKnowledgePrototype
from validate_academic_knowledge_v03 import validate_document, validation_report

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output/academic_knowledge_v03"
BASELINE = "GS-EDX-9MA0-STAT"
CTX = "CTX-EDX-9MA0-STAT"
DISCUSSION = "LOC-GOLD-DISCUSSION"
QP = "SRC-9MA0-2025-31-QP"
MS = "SRC-9MA0-2025-31-MS"


def prov():
    return {"origin": "real", "creation_method": "ai", "source_references": [f"locator:{DISCUSSION}"]}


def ref(kind, identifier):
    return {"kind": kind, "id": identifier}


def part_id(label):
    return f"QP-9MA0-2025-31-{label}"


COMPETENCIES = [
    ("MEAN-CALC", "Calculate the mean", "approved"),
    ("MEDIAN-DETERMINE", "Determine the median", "approved"),
    ("MODE-DETERMINE", "Determine the mode", "approved"),
    ("PERCENTILES-DETERMINE", "Determine percentiles", "approved"),
    ("RANGE-DETERMINE", "Determine the range", "approved"),
    ("INTERPERCENTILE-RANGE-DETERMINE", "Determine an interpercentile range", "approved"),
    ("VARIANCE-CALC", "Calculate variance", "approved"),
    ("SD-CALC", "Calculate standard deviation", "approved"),
    ("VARIATION-INTERPRET", "Interpret measures of variation", "approved"),
    ("DATA-CLEAN", "Clean data for statistical analysis", "strong_candidate"),
    ("CODING-USE", "Use coding in statistical calculations", "strong_candidate"),
    ("CENTRAL-TENDENCY-INTERPRET", "Interpret measures of central tendency", "strong_candidate"),
    ("CONTEXT-INFER", "Make contextual inferences using statistical evidence", "candidate"),
    ("MODEL-PARAM-INTERPRET", "Interpret parameters of a statistical model in context", "candidate"),
    ("DATA-CLASSIFY", "Classify statistical data", "candidate"),
]
CONCEPTS = [
    ("CON-STAT-MEAN", "Mean"), ("CON-STAT-MEDIAN", "Median"), ("CON-STAT-MODE", "Mode"),
    ("CON-STAT-PERCENTILE", "Percentile"), ("CON-STAT-RANGE", "Range"),
    ("CON-STAT-INTERPERCENTILE-RANGE", "Interpercentile range"), ("CON-STAT-VARIANCE", "Variance"),
    ("CON-STAT-SD", "Standard deviation"), ("CON-STAT-DISCRETE", "Discrete data"),
    ("CON-STAT-CONTINUOUS", "Continuous data"), ("CON-STAT-GROUPED", "Grouped data"),
    ("CON-STAT-UNGROUPED", "Ungrouped data"),
    ("CON-STAT-REGRESSION-LINE", "Regression line"), ("CON-MATH-Y-INTERCEPT", "y-intercept"),
]


def build_prototype():
    data = {name: [] for name in AcademicKnowledgePrototype.model_fields
            if name not in {"schema_version", "purpose", "evidence_notice"}}
    data["evidence_notice"] = (
        "Working baseline transcribed from the prior human discussion by AI. "
        "Original specification, question paper and mark scheme have NOT been verified in this import. "
        "Official locators are provisional labels; observations are inherited paraphrases, not quotations. "
        "Gold Standard approval is not registry approval, source verification, or student mastery. "
        "This is a five-part sample, not complete paper coverage."
    )
    for identifier, title, source_type in [
        ("SRC-9MA0-SPEC", "Edexcel 9MA0 specification (exact edition unverified)", "official_syllabus"),
        (QP, "June 2025 9MA0/31 Question paper (identity inherited, file unverified)", "official_past_paper"),
        (MS, "June 2025 9MA0/31 Mark scheme (identity inherited, file unverified)", "official_mark_scheme"),
        ("SRC-GOLD-DISCUSSION", "分析学校智能系统工作量 — Gold Standard v0.1 discussion", "other"),
    ]:
        data["sources"].append({"source_id": identifier, "title": title, "source_type": source_type,
                                "origin": "real", "verification_status": "unverified"})
    data["locators"].append({"locator_id": DISCUSSION, "source_id": "SRC-GOLD-DISCUSSION",
                             "locator_kind": "conversation_item", "label": "Gold Standard v0.1 Consolidated Draft and Q2/Q4 discussion",
                             "anchor": "chatgpt-conversation://6aa2488a-4e2c-83ed-8024-3ec92658a045"})
    data["contexts"].append({"context_id": CTX, "exam_board": "Pearson Edexcel",
                             "qualification": "A Level Mathematics", "subject": "Mathematics",
                             "specification_code": "9MA0", "provenance": prov()})

    def gold(label, category, disposition, target=None, rationale=None):
        data["gold_standard_entries"].append({
            "entry_id": f"GS-ENTRY-{len(data['gold_standard_entries']) + 1:02d}",
            "baseline_id": BASELINE, "baseline_version": "0.1", "label": label,
            "category": category, "disposition": disposition, "target": target,
            "rationale": rationale or "Inherited working conclusion from the prior consolidated baseline; not a new approval.",
            "decision_source_reference": DISCUSSION, "provenance": prov(),
        })

    for suffix, name, working_status in COMPETENCIES:
        identifier = f"CAN-STAT-{suffix}"
        data["competencies"].append({"canonical_id": identifier, "subject_domain": "Statistics",
                                     "skill_name": name, "status": "draft", "provenance": prov()})
        gold(name, "competency", working_status, ref("competency", identifier))
    for i, (identifier, name) in enumerate(CONCEPTS):
        data["concepts"].append({"concept_id": identifier,
                                "subject_domain": "Mathematics" if identifier == "CON-MATH-Y-INTERCEPT" else "Statistics",
                                "name": name, "description": f"The concept of {name}; distinct from an action using it.",
                                "provenance": prov()})
        if i < 12:
            gold(name, "concept", "recorded", ref("concept", identifier))

    for q in ("Q2", "Q4"):
        loc = f"LOC-QP-{q}"
        data["locators"].append({"locator_id": loc, "source_id": QP, "locator_kind": "section", "label": q,
                                 "assessment_question_id": f"Q-9MA0-2025-31-{q}"})
        data["questions"].append({"question_id": f"Q-9MA0-2025-31-{q}", "paper_source_id": QP,
                                  "label": q, "source_locator_id": loc, "curriculum_context_id": CTX, "provenance": prov()})
    labels = [("Q2-a", "Q2(a)"), ("Q2-b", "Q2(b)"), ("Q2-c", "Q2(c)"),
              ("Q4-b", "Q4(b)"), ("Q4-c", "Q4(c)"), ("Q4-c-ii", "Q4(c)(ii)")]
    for suffix, label in labels:
        pid = part_id(suffix)
        for prefix, source in (("QP", QP), ("MS", MS)):
            data["locators"].append({"locator_id": f"LOC-{prefix}-{suffix}", "source_id": source,
                                     "locator_kind": "question_part", "label": label, "assessment_part_id": pid})
        data["question_parts"].append({"part_id": pid, "question_id": f"Q-9MA0-2025-31-{suffix[:2]}",
                                       "label": label, "node_kind": "container" if suffix == "Q4-c" else "assessable",
                                       "source_locator_id": f"LOC-QP-{suffix}",
                                       "parent_part_id": part_id("Q4-c") if suffix == "Q4-c-ii" else None,
                                       "provenance": prov()})

    def evidence(target, locator, observation):
        eid = f"EV-{len(data['evidence']) + 1:03d}"
        data["evidence"].append({"evidence_id": eid, "source_locator_ids": [locator], "target": target,
                                 "observation": observation, "content_kind": "paraphrase", "evidence_role": "supports",
                                 "observation_status": "observed", "provenance": prov()})
        return eid

    for suffix, competency, extent, concepts, observation in [
        ("Q2-a", "MEAN-CALC", "undetermined", ["CON-STAT-MEAN"], "Inherited analysis: calculate the mean using the supplied summary statistics."),
        ("Q2-b", "SD-CALC", "undetermined", ["CON-STAT-SD"], "Inherited analysis: calculate standard deviation from summary statistics."),
        ("Q2-c", "VARIATION-INTERPRET", "partial", [], "Inherited analysis: interpret differences in variation/spread in the running context."),
        ("Q2-c", "CONTEXT-INFER", "undetermined", [], "Inherited analysis: use the variation evidence to make a contextual inference; competency remains Candidate."),
        ("Q4-b", "DATA-CLEAN", "partial", [], "Inherited analysis: identify possible tr/trace rainfall entries. This is partial evidence, not demonstration of a complete cleaning workflow."),
        ("Q4-c-ii", "MODEL-PARAM-INTERPRET", "partial", ["CON-STAT-REGRESSION-LINE", "CON-MATH-Y-INTERCEPT"],
         "Inherited analysis: at zero sunshine, predicted/average rainfall is approximately 0.741 mm; minimum rain is not the accepted interpretation."),
    ]:
        mid = f"MAP-{suffix}-{competency}"
        evs = [evidence(ref("part_mapping", mid), f"LOC-{prefix}-{suffix}", observation) for prefix in ("QP", "MS")]
        data["part_mappings"].append({"mapping_id": mid, "part_id": part_id(suffix),
                                      "canonical_id": f"CAN-STAT-{competency}", "role": "assessed",
                                      "assessment_extent": extent, "rationale": observation,
                                      "focus_concept_ids": concepts, "mapping_method": "ai",
                                      "evidence_ids": evs, "provenance": prov()})

    for suffix, concept in [("MEAN-CALC", "CON-STAT-MEAN"), ("SD-CALC", "CON-STAT-SD"),
                            ("MODEL-PARAM-INTERPRET", "CON-STAT-REGRESSION-LINE"),
                            ("MODEL-PARAM-INTERPRET", "CON-MATH-Y-INTERCEPT")]:
        lid = f"LINK-{suffix}-{concept}"
        reason = "A discussed application of the concept; this link is not an exhaustive competency definition."
        data["concept_links"].append({"link_id": lid, "canonical_id": f"CAN-STAT-{suffix}",
                                      "concept_id": concept, "rationale": reason,
                                      "evidence_ids": [evidence(ref("concept_link", lid), DISCUSSION, reason)], "provenance": prov()})

    data["resources"].append({"resource_id": "RES-PEARSON-LDS", "name": "Pearson Large Data Set",
                              "description": "Dataset identity inherited from the discussion; workbook content and version not imported.",
                              "provenance": prov()})
    for suffix in ("Q4-b", "Q4-c-ii"):
        uid = f"USE-{suffix}-LDS"
        reason = "Inherited analysis: this part uses the Pearson LDS weather context."
        data["resource_uses"].append({"use_id": uid, "resource_id": "RES-PEARSON-LDS",
                                      "target": ref("question_part", part_id(suffix)), "relationship": "uses_context",
                                      "description": reason, "evidence_ids": [evidence(ref("resource_use", uid), f"LOC-QP-{suffix}", reason)],
                                      "provenance": prov()})
    conditions = [
        ("COND-Q2-SUMMARY", "Q2", "input_form", "given_in_question", None, "LOC-QP-Q2",
         "Inherited analysis: summary statistics are supplied; numerical values are not transcribed.", ["Q2-a", "Q2-b"]),
        ("COND-Q4-WEATHER", "Q4", "context_detail", "given_in_question", None, "LOC-QP-Q4",
         "Inherited analysis: Leeming 2015; sunshine is x and rainfall is y.", ["Q4-b", "Q4-c-ii"]),
        ("COND-Q4-TRACE", "Q4", "context_detail", "recalled_from_resource", "RES-PEARSON-LDS", "LOC-MS-Q4-b",
         "Inherited analysis: rainfall entries may include tr/trace; identifying the issue is the observed demand.", ["Q4-b"]),
        ("COND-Q4-c-ii-LINE", "Q4", "given_model", "given_in_question", None, "LOC-QP-Q4-c-ii",
         "Inherited analysis: y = 0.741 + 0.199x is the given regression model.", ["Q4-c-ii"]),
    ]
    for cid, q, kind, availability, resource, locator, description, parts in conditions:
        data["task_conditions"].append({"condition_id": cid, "question_id": f"Q-9MA0-2025-31-{q}",
                                        "kind": kind, "availability": availability, "resource_id": resource,
                                        "description": description,
                                        "evidence_ids": [evidence(ref("condition", cid), locator, description)], "provenance": prov()})
        data["part_condition_links"].extend({"part_id": part_id(p), "condition_id": cid} for p in parts)
    gold("From summary statistics", "condition", "recorded", ref("condition", "COND-Q2-SUMMARY"),
         "Shared task condition for Q2(a/b); no universal curriculum requirement inferred.")
    gold("Grouped-data percentiles using linear interpolation", "scope", "recorded", rationale=
         "Preserved scope/method note; objective locator not verified, so no official scope record manufactured.")
    gold("Discrete / continuous / grouped / ungrouped data", "scope", "recorded", rationale=
         "Preserved curriculum scope note from baseline; exact official objective remains unregistered.")
    gold("Pearson Large Data Set", "resource", "recorded", ref("resource", "RES-PEARSON-LDS"))
    gold("tr / trace rainfall entry", "condition", "recorded", ref("condition", "COND-Q4-TRACE"))
    gold("Qualitative / Quantitative", "concept", "deferred", rationale="Deferred from this working baseline; not curriculum exclusion.")
    gold("Quartiles", "concept", "deferred", rationale="Deferred from this working baseline; not curriculum exclusion.")
    return validate_document(data)


def main():
    model = build_prototype()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prototype.json").write_text(json.dumps(model.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = validation_report(model)
    (OUT / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"structure_valid": report["structure_valid"], "source_verified": report["source_verified"],
                      "counts": report["counts"], "output": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
