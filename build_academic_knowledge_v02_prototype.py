"""Build a parallel v0.2 artifact; never run or modify the v0.1 pipeline."""

import json

from academic_knowledge_schema_v02 import SYNTHETIC_NOTICE
from validate_academic_knowledge_v02 import DEFAULT_FILE, load_real_sources, validate_document

REGION = "CAN-ALG-INEQ-REGION-INTERPRET"
VECTOR = "CAN-MATH-VECTOR-ADD"
MATRIX_CONTEXT = "SYN-CTX-MATRIX"
MATRIX_OBJECTIVE = "SYN-OBJ-MATRIX-BASIC"


def provenance(reference, synthetic=False):
    return {
        "origin": "synthetic" if synthetic else "real",
        "source_reference": reference,
        "synthetic_notice": SYNTHETIC_NOTICE if synthetic else None,
    }


def synthetic(reference):
    return provenance(f"synthetic://architecture-v02/{reference}", True)


def build_prototype():
    sources = load_real_sources()
    data = {key: [] for key in (
        "contexts", "competencies", "objective_references", "scopes", "evidence",
        "mappings", "questions", "question_mappings", "question_difficulties",
    )}
    region = next(n for n in sources["graph"]["canonical_objectives"] if n["canonical_id"] == REGION)
    data["competencies"].append({
        **region, "provenance": provenance(f"output/topic2_canonical_promoted.json#{REGION}")
    })
    decision = next(d for d in sources["decisions"] if d["approved_canonical_id"] == REGION)
    # Stable registry IDs for this local snapshot; no invented syllabus version.
    for source_id, context_id in (
        ("EDX-4MA1-F-2.8-E", "CTX-EDX-4MA1-F-LOCAL-BASELINE"),
        ("EDX-4MA1-H-2.8-B", "CTX-EDX-4MA1-H-LOCAL-BASELINE"),
    ):
        source, curriculum, official = sources["objectives"][source_id]
        data["contexts"].append({
            "context_id": context_id,
            **{k: curriculum[k] for k in ("exam_board", "qualification", "subject", "specification_code")},
            "tier": curriculum["tier_source"], "provenance": provenance(source),
        })
        data["objective_references"].append({
            "official_source_id": source_id, "context_id": context_id,
            "wording_excerpt": official["official_text"],
            "provenance": provenance(f"{source}#{source_id}"),
        })
        scope = next(s for s in sources["scopes"] if
                     s["official_source_id"] == source_id and s["canonical_id"] == REGION)
        scope_id = f"SCOPE-{source_id}-REGION"
        support_id, clarify_id = f"EV-{source_id}-SUPPORT", f"EV-{source_id}-SCOPE"
        data["scopes"].append({
            "scope_id": scope_id, "official_source_id": source_id,
            "canonical_id": REGION, "context_id": context_id,
            **{k: scope[k] for k in ("scope_description", "constraints", "review_status")},
            "evidence_ids": [clarify_id],
            "provenance": provenance(f"output/topic2_scope_metadata_prototype.json#{source_id}/{REGION}"),
        })
        for identifier, role, scope_reference in (
            (support_id, "supports", None), (clarify_id, "clarifies", scope_id)
        ):
            data["evidence"].append({
                "evidence_id": identifier, "official_source_id": source_id,
                "context_id": context_id, "canonical_id": REGION, "scope_id": scope_reference,
                "source_type": "official_syllabus", "authority": "official_requirement",
                "observation": official["official_text"], "evidence_role": role,
                "observation_status": "observed",
                # New v0.2 evidence annotations have not received separate human review.
                "review_status": "pending", "provenance": provenance(f"{source}#{source_id}"),
            })
        mapping = next(m for m in sources["graph"]["mappings"] if
                       m["official_source_id"] == source_id and m["canonical_id"] == REGION)
        data["mappings"].append({
            **mapping, "context_id": context_id, "evidence_ids": [support_id],
            "human_review_decision_id": decision["decision_id"],
            "provenance": provenance(f"output/topic2_canonical_promoted.json#{source_id}/{REGION}"),
        })

    data["competencies"].append({
        "canonical_id": VECTOR, "subject_domain": "Vectors", "skill_name": "Add vectors",
        "description": "Determine the sum of vectors.", "provenance": synthetic("vector/competency"),
    })
    for label, qualification, stage, constraints in (
        ("A", "IGCSE-like", "secondary-like", ["2D vectors", "numeric components", "direct calculations"]),
        ("B", "A-Level-like", "upper-secondary-like", ["2D and 3D vectors", "algebraic components", "multi-step applications"]),
    ):
        context_id, source_id = f"SYN-CTX-VECTOR-{label}", f"SYN-OBJ-VECTOR-{label}"
        scope_id, evidence_id = f"SYN-SCOPE-VECTOR-{label}", f"SYN-EV-VECTOR-{label}"
        data["contexts"].append({
            "context_id": context_id, "exam_board": f"Synthetic board {label}",
            "qualification": qualification, "subject": "Mathematics",
            "educational_stage": stage, "curriculum_version": "synthetic-fixture-v1",
            "provenance": synthetic(f"vector/{label}/context"),
        })
        data["objective_references"].append({
            "official_source_id": source_id, "context_id": context_id,
            "wording_excerpt": "Add vectors.", "provenance": synthetic(f"vector/{label}/objective"),
        })
        data["scopes"].append({
            "scope_id": scope_id, "official_source_id": source_id,
            "context_id": context_id, "canonical_id": VECTOR,
            "scope_description": "; ".join(constraints), "constraints": constraints,
            "included_applications": [constraints[-1]], "evidence_ids": [evidence_id],
            "provenance": synthetic(f"vector/{label}/scope"),
        })
        data["evidence"].append({
            "evidence_id": evidence_id, "official_source_id": source_id,
            "context_id": context_id, "canonical_id": VECTOR, "scope_id": scope_id,
            "source_type": "official_specification_note", "authority": "official_requirement",
            "observation": f"Synthetic specification-note example: {'; '.join(constraints)}.",
            "evidence_role": "clarifies", "observation_status": "observed",
            "provenance": synthetic(f"vector/{label}/specification-note"),
        })
        data["mappings"].append({
            "official_source_id": source_id, "context_id": context_id, "canonical_id": VECTOR,
            "relationship": "narrower", "confidence": 0.9, "mapping_method": "human",
            "evidence_ids": [evidence_id], "provenance": synthetic(f"vector/{label}/mapping"),
        })

    data["contexts"].append({
        "context_id": MATRIX_CONTEXT, "exam_board": "Synthetic board C",
        "qualification": "Synthetic matrix curriculum", "subject": "Mathematics",
        "provenance": synthetic("matrix/context"),
    })
    data["objective_references"].append({
        "official_source_id": MATRIX_OBJECTIVE, "context_id": MATRIX_CONTEXT,
        "wording_excerpt": "Understand basic operations on matrices.",
        "provenance": synthetic("matrix/objective"),
    })
    data["evidence"].append({
        "evidence_id": "SYN-EV-MATRIX-AMBIGUOUS", "official_source_id": MATRIX_OBJECTIVE,
        "context_id": MATRIX_CONTEXT, "source_type": "official_syllabus",
        "authority": "official_requirement", "evidence_role": "clarifies",
        "observation_status": "ambiguous",
        "observation": "Synthetic broad wording does not enumerate which matrix operations are required.",
        "provenance": synthetic("matrix/syllabus-like-wording"),
    })
    for operation, name in (
        ("ADD", "Add matrices"), ("SUBTRACT", "Subtract matrices"),
        ("SCALAR-MULTIPLY", "Multiply a matrix by a scalar"),
        ("MULTIPLY", "Multiply matrices"), ("INVERSE", "Find an inverse matrix"),
    ):
        canonical_id = f"CAN-MATH-MATRIX-{operation}"
        scope_id, evidence_id = f"SYN-SCOPE-MATRIX-{operation}", f"SYN-EV-MATRIX-{operation}"
        absent = operation == "INVERSE"
        data["competencies"].append({
            "canonical_id": canonical_id, "subject_domain": "Matrices", "skill_name": name,
            "description": name + ".", "provenance": synthetic(f"matrix/{operation}/candidate"),
        })
        data["scopes"].append({
            "scope_id": scope_id, "official_source_id": MATRIX_OBJECTIVE,
            "context_id": MATRIX_CONTEXT, "canonical_id": canonical_id,
            "scope_description": "Unresolved candidate interpretation" if absent else "Supported candidate interpretation; official coverage remains unconfirmed",
            "unresolved_scope": ["Whether inverse matrices are required"] if absent else ["Official coverage and limits require clarification"],
            "evidence_ids": ["SYN-EV-MATRIX-AMBIGUOUS", evidence_id],
            "provenance": synthetic(f"matrix/{operation}/scope"),
        })
        data["evidence"].append({
            "evidence_id": evidence_id, "official_source_id": MATRIX_OBJECTIVE,
            "context_id": MATRIX_CONTEXT, "canonical_id": canonical_id, "scope_id": scope_id,
            "source_type": "official_past_paper", "authority": "official_assessment",
            "observation": (
                "Synthetic past-paper-like sample examined did not contain inverse matrices. This is not evidence of exclusion."
                if absent else f"Synthetic past-paper-like sample contains an example of: {name}."
            ),
            "evidence_role": "clarifies" if absent else "supports",
            "observation_status": "not_observed" if absent else "observed",
            "application": name, "provenance": synthetic(f"matrix/examined-sample/{operation}"),
        })
        if not absent:
            data["mappings"].append({
                "official_source_id": MATRIX_OBJECTIVE, "context_id": MATRIX_CONTEXT,
                "canonical_id": canonical_id, "relationship": "broader", "confidence": 0.7,
                "mapping_method": "human", "evidence_ids": ["SYN-EV-MATRIX-AMBIGUOUS", evidence_id],
                "provenance": synthetic(f"matrix/{operation}/candidate-mapping"),
            })
    data["evidence"].append({
        "evidence_id": "SYN-EV-MATRIX-TEXTBOOK", "official_source_id": MATRIX_OBJECTIVE,
        "context_id": MATRIX_CONTEXT, "canonical_id": "CAN-MATH-MATRIX-ADD",
        "source_type": "third_party_textbook", "authority": "third_party_material",
        "observation": "Synthetic textbook-like example illustrates matrix addition; it does not define syllabus coverage.",
        "evidence_role": "supports", "observation_status": "observed",
        "provenance": synthetic("matrix/textbook-like-example"),
    })
    # Two tasks in the SAME context and skill, with different illustrative difficulty.
    for label, prediction, steps, scaffolding in (
        ("DIRECT", 0.25, 1, "substantial"), ("MULTISTEP", 0.75, 4, "none")
    ):
        question_id = f"SYN-Q-VECTOR-{label}"
        data["questions"].append({
            "question_id": question_id, "source_type": "other",
            "curriculum_context_id": "SYN-CTX-VECTOR-A",
            "provenance": synthetic(f"questions/{label}"),
        })
        data["question_mappings"].append({
            "question_id": question_id, "canonical_id": VECTOR, "confidence": 0.9,
        })
        data["question_difficulties"].append({
            "question_id": question_id, "predicted_difficulty": prediction,
            "reasoning_steps": steps, "scaffolding_level": scaffolding,
            "context_familiarity": "familiar" if label == "DIRECT" else "novel",
            "difficulty_method": "expert_estimate" if label == "DIRECT" else "mixed",
            "observed_difficulty": None if label == "DIRECT" else 0.6,
            "observed_sample_size": None if label == "DIRECT" else 40,
            "provenance": synthetic(f"questions/{label}/simulated-measurement-not-student-data"),
        })
    return validate_document(data, sources)


def main():
    prototype = build_prototype()
    # Fixed, new-only destination. No option to overwrite an existing v0.1 artifact.
    DEFAULT_FILE.write_text(
        json.dumps(prototype.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {DEFAULT_FILE.name}")
    print(SYNTHETIC_NOTICE)
    print("Real case: 2 Edexcel objectives -> 1 competency -> 2 distinct scopes")
    print("Synthetic inverse matrices: NOT OBSERVED; unresolved, never excluded")


if __name__ == "__main__":
    main()
