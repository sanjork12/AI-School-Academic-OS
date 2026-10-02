"""Behavior and failure-path tests; changes only in memory and disposable test directories."""
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from academic_knowledge_schema_v03 import AcademicKnowledgePrototype, SYNTHETIC_NOTICE, SourceDocument, SourceLocator
from build_academic_knowledge_v03_prototype import build_prototype, part_id, prov, ref, CTX, QP, MS
from validate_academic_knowledge_v03 import (validate_document, validation_report, ExternalTrust,
    SourceVerification, LocatorVerification, digest, content_digest, review_content_digest)


class V03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = build_prototype().model_dump()

    def setUp(self):
        self.data = copy.deepcopy(self.base)
        self.trust = ExternalTrust()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def invalid(self, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            validate_document(self.data, self.trust)

    def find(self, collection, field, value):
        return next(r for r in self.data[collection] if r[field] == value)

    def mapping(self, label="Q2-a"):
        return next(m for m in self.data["part_mappings"] if m["part_id"] == part_id(label))

    def external_verify(self, source_id):
        """Test-only trusted material, NOT actual Pearson verification; never written to the prototype."""
        source = self.find("sources", "source_id", source_id)
        artifact = Path(self.temp.name) / (source_id + ".txt")
        text = "TEST ONLY: This is not an official paper. Example verified text."
        artifact.write_text(text, encoding="utf-8")
        source.update(verification_status="verified", artifact_reference=str(artifact),
                      content_digest=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                      verification_reference=f"test-registry:{source_id}")
        source.update(SourceDocument.model_validate(source).model_dump())
        self.trust.sources[source["verification_reference"]] = SourceVerification(digest(source), artifact, source["content_digest"])
        for loc in self.data["locators"]:
            if loc["source_id"] == source_id:
                loc.update(verification_status="verified", verification_reference=f"test-registry:{loc['locator_id']}")
                loc.update(SourceLocator.model_validate(loc).model_dump())
                self.trust.locators[loc["verification_reference"]] = LocatorVerification(digest(loc), source["content_digest"], text)

    def approve(self, record, target, registry=False):
        identifier = f"TEST-REVIEW-{len(self.data['review_decisions']) + 1}"
        if registry:
            record.update(status="approved", registry_decision_id=identifier)
        else:
            record.update(review_status="approved", review_decision_id=identifier)
        decision = {"decision_id": identifier, "target": target, "target_content_digest": review_content_digest(self.data, target),
                    "decision": "approved", "reviewer_reference": "test-only-reviewer",
                    "decision_source_reference": f"external-test:{identifier}", "rationale": "Test harness attestation, not a real approval.",
                    "supersedes_decision_id": None}
        self.data["review_decisions"].append(decision)
        self.trust.decisions[decision["decision_source_reference"]] = digest(decision)
        return decision

    def add_scope(self):
        self.data["locators"].append({"locator_id": "LOC-TEST-SPEC", "source_id": "SRC-9MA0-SPEC",
                                      "locator_kind": "section", "label": "Test-only artificial section"})
        self.data["objective_references"].append({"objective_id": "OBJ-TEST", "context_id": CTX,
                                                   "source_locator_id": "LOC-TEST-SPEC", "provenance": prov()})
        scope = {"scope_id": "SCOPE-TEST", "objective_id": "OBJ-TEST", "canonical_id": "CAN-STAT-MEAN-CALC",
                 "context_id": CTX, "scope_description": "Test-only scope", "provenance": prov(), "evidence_ids": [],
                 "excluded_applications": []}
        self.data["scopes"].append(scope)
        return scope

    def add_exclusion(self):
        scope = self.add_scope()
        self.external_verify("SRC-9MA0-SPEC")
        e = {"evidence_id": "EV-TEST-EXCLUSION", "source_locator_ids": ["LOC-TEST-SPEC"],
             "target": ref("scope", "SCOPE-TEST"), "observation": "Test-only explicit exclusion of application X.",
             "content_kind": "paraphrase", "evidence_role": "supports", "observation_status": "observed",
             "explicit_exclusion": True, "application": "X", "provenance": prov()}
        self.data["evidence"].append(e)
        x = {"exclusion_id": "EX-TEST", "application": "X", "evidence_ids": [e["evidence_id"]],
             "rationale": "Test-only explicit boundary", "provenance": prov()}
        scope["excluded_applications"].append(x)
        # Normalize defaults before binding trusted review digests.
        self.data = AcademicKnowledgePrototype.model_validate(self.data).model_dump()
        e = self.find("evidence", "evidence_id", e["evidence_id"])
        scope = self.find("scopes", "scope_id", "SCOPE-TEST")
        x = scope["excluded_applications"][0]
        self.approve(e, ref("evidence", e["evidence_id"]))
        self.approve(x, ref("scope_exclusion", x["exclusion_id"]))
        return scope, e, x

    def test_baseline_statuses_do_not_promote_registry(self):
        model = validate_document(self.data)
        statuses = Counter(g.disposition for g in model.gold_standard_entries if g.category == "competency")
        self.assertEqual(statuses, {"approved": 9, "strong_candidate": 3, "candidate": 3})
        self.assertTrue(all(c.status == "draft" for c in model.competencies))
        self.assertEqual(len(model.competencies), 15)

    def test_deterministic_roundtrip(self):
        self.assertEqual(build_prototype().model_dump(), self.base)
        self.assertEqual(validate_document(json.loads(json.dumps(self.data))).model_dump(), self.base)

    def test_saved_artifact_matches_builder(self):
        file = Path(__file__).parent / "output/academic_knowledge_v03/prototype.json"
        self.assertTrue(file.exists())
        self.assertEqual(json.loads(file.read_text(encoding="utf-8")), self.base)

    def test_five_assessable_parts_and_container(self):
        self.assertEqual(Counter(p["node_kind"] for p in self.data["question_parts"]), {"assessable": 5, "container": 1})
        self.assertEqual(self.find("question_parts", "part_id", part_id("Q4-c-ii"))["parent_part_id"], part_id("Q4-c"))

    def test_concept_cannot_substitute_competency(self):
        self.mapping()["canonical_id"] = "CON-STAT-MEAN"
        self.invalid("Unknown competency")

    def test_competency_cannot_substitute_concept(self):
        self.data["concept_links"][0]["concept_id"] = "CAN-STAT-MEAN-CALC"
        self.invalid("Unknown concept")

    def test_no_curriculum_identity_or_mastery_fields_on_competency(self):
        for field in ("exam_board", "tier", "difficulty", "parent_id", "mastery"):
            with self.subTest(field=field):
                d = copy.deepcopy(self.base)
                d["competencies"][0][field] = "X"
                with self.assertRaises(ValueError):
                    validate_document(d)
        for field in ("student_mastery", "learning_requirements", "mastery_criteria", "hierarchy"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_document({**self.base, field: []})

    def test_deferred_items_are_not_nodes_or_exclusions(self):
        deferred = [g for g in self.data["gold_standard_entries"] if g["disposition"] == "deferred"]
        self.assertEqual({g["label"] for g in deferred}, {"Quartiles", "Qualitative / Quantitative"})
        self.assertTrue(all(g["target"] is None for g in deferred))
        self.assertEqual(self.data["scopes"], [])

    def test_gold_target_type_and_duplicate(self):
        self.data["gold_standard_entries"][0]["target"] = ref("concept", "CON-STAT-REGRESSION-LINE")
        self.invalid("category/target")
        self.data = copy.deepcopy(self.base)
        extra = copy.deepcopy(self.data["gold_standard_entries"][0]); extra["entry_id"] = "ANOTHER"
        self.data["gold_standard_entries"].append(extra)
        self.invalid("Duplicate baseline target")

    def test_shared_conditions_are_explicit_only(self):
        def conditions(label):
            return {x["condition_id"] for x in self.data["part_condition_links"] if x["part_id"] == part_id(label)}
        self.assertEqual(conditions("Q2-a"), {"COND-Q2-SUMMARY"})
        self.assertEqual(conditions("Q2-b"), {"COND-Q2-SUMMARY"})
        self.assertEqual(conditions("Q2-c"), set())
        self.assertNotIn("COND-Q4-TRACE", conditions("Q4-c-ii"))

    def test_cross_question_condition_rejected(self):
        self.data["part_condition_links"][0]["part_id"] = part_id("Q4-b")
        self.invalid("Cross-question condition")

    def test_unknown_condition_and_duplicate_attachment(self):
        self.data["part_condition_links"][0]["condition_id"] = "MISSING"
        self.invalid("Unknown condition")
        self.data = copy.deepcopy(self.base)
        self.data["part_condition_links"].append(copy.deepcopy(self.data["part_condition_links"][0]))
        self.invalid("Duplicate part condition")

    def test_recalled_condition_requires_resource(self):
        self.find("task_conditions", "condition_id", "COND-Q4-TRACE")["resource_id"] = None
        self.invalid("Recalled condition requires resource")

    def test_parent_cycle(self):
        self.find("question_parts", "part_id", part_id("Q4-c"))["parent_part_id"] = part_id("Q4-c")
        self.invalid("parent cycle")

    def test_cross_question_parent(self):
        self.find("question_parts", "part_id", part_id("Q2-a"))["parent_part_id"] = part_id("Q4-c")
        self.invalid("Cross-question parent")

    def test_unknown_parent(self):
        self.find("question_parts", "part_id", part_id("Q4-c-ii"))["parent_part_id"] = "MISSING"
        self.invalid("Unknown question_part")

    def test_assessable_parent_not_container(self):
        self.find("question_parts", "part_id", part_id("Q2-b"))["parent_part_id"] = part_id("Q2-a")
        self.invalid("Parent must be a container")

    def test_container_mapping_rejected(self):
        self.mapping("Q4-c-ii")["part_id"] = part_id("Q4-c")
        self.invalid("Container cannot carry")

    def test_many_to_many_and_roles(self):
        q2c = [m for m in self.data["part_mappings"] if m["part_id"] == part_id("Q2-c")]
        self.assertEqual(len(q2c), 2)
        extra = copy.deepcopy(self.mapping())
        extra.update(mapping_id="MAP-SUPPORT", part_id=part_id("Q2-b"), evidence_ids=[], role="supporting")
        self.data["part_mappings"].append(extra)
        model = validate_document(self.data)
        self.assertEqual(len([m for m in model.part_mappings if m.canonical_id == "CAN-STAT-MEAN-CALC"]), 2)
        self.assertEqual(len([m for m in model.part_mappings if m.role == "supporting"]), 1)

    def test_duplicate_mapping_pair_rejected_even_with_new_id(self):
        extra = copy.deepcopy(self.mapping()); extra["mapping_id"] = "DUPLICATE"
        self.data["part_mappings"].append(extra)
        self.invalid("Duplicate part competency pair")

    def test_primary_and_score_weights_not_accepted(self):
        self.mapping()["primary"] = True
        self.invalid("Extra inputs")

    def test_partial_data_cleaning_retained(self):
        self.assertEqual(self.mapping("Q4-b")["assessment_extent"], "partial")
        self.assertEqual(self.mapping("Q4-c-ii")["assessment_extent"], "partial")

    def test_resource_reused_without_curriculum_requirement(self):
        self.assertEqual({u["resource_id"] for u in self.data["resource_uses"]}, {"RES-PEARSON-LDS"})
        self.assertEqual(len(self.data["resource_uses"]), 2)
        self.assertFalse(any(u["relationship"] == "familiarity_required" for u in self.data["resource_uses"]))

    def test_resource_use_target_relationship(self):
        self.data["resource_uses"][0]["relationship"] = "familiarity_required"
        self.invalid("relationship/target")

    def test_evidence_wrong_part(self):
        self.data["evidence"][0]["source_locator_ids"] = ["LOC-QP-Q4-b"]
        self.invalid("Assessment evidence part mismatch")

    def test_resource_evidence_wrong_part(self):
        ev = next(e for e in self.data["evidence"] if e["target"]["kind"] == "resource_use")
        ev["source_locator_ids"] = ["LOC-QP-Q2-a"]
        self.invalid("Resource evidence part mismatch")

    def test_condition_evidence_wrong_question(self):
        ev = next(e for e in self.data["evidence"] if e["target"] == ref("condition", "COND-Q2-SUMMARY"))
        ev["source_locator_ids"] = ["LOC-QP-Q4"]
        self.invalid("Task evidence question mismatch")

    def test_mismatched_evidence_target(self):
        self.mapping()["evidence_ids"] = self.mapping("Q2-b")["evidence_ids"]
        self.invalid("Attached evidence target mismatch")

    def test_evidence_cannot_mix_documents(self):
        self.data["evidence"][0]["source_locator_ids"].append("LOC-MS-Q2-a")
        self.invalid("cannot mix source documents")

    def test_authority_not_editable_and_correctly_derived(self):
        model = validate_document(self.data)
        self.assertEqual(next(s for s in model.sources if s.source_id == QP).authority, "official_assessment")
        self.data["sources"][1]["authority"] = "official_requirement"
        self.invalid("Extra inputs")

    def test_real_unverified_structure_passes_with_explicit_failure_readiness(self):
        result = validation_report(self.data)
        self.assertTrue(result["structure_valid"])
        self.assertFalse(result["source_verified"])
        self.assertEqual(len(result["selected_targets"]), 6)
        self.assertTrue(all(not r["source_verified"] for r in result["selected_targets"]))

    def test_verified_flag_alone_not_trusted(self):
        s = self.data["sources"][1]
        s.update(verification_status="verified", content_digest="a" * 64,
                 artifact_reference="fake.pdf", verification_reference="invented")
        self.invalid("Untrusted source verification")

    def test_source_and_locator_verification_happy_path_not_approval(self):
        self.external_verify(QP); self.external_verify(MS)
        report = validation_report(self.data, trust=self.trust)
        self.assertTrue(report["source_verified"])
        self.assertTrue(all(r["review_status"] == "pending" for r in report["selected_targets"]))
        self.assertTrue(all(c["status"] == "draft" for c in self.data["competencies"]))

    def test_missing_one_locator_keeps_one_target_unverified(self):
        self.external_verify(QP); self.external_verify(MS)
        self.find("locators", "locator_id", "LOC-MS-Q2-a")["verification_status"] = "unverified"
        report = validation_report(self.data, trust=self.trust)
        self.assertFalse(report["source_verified"])
        self.assertEqual(sum(r["source_verified"] for r in report["selected_targets"]), 5)

    def test_changed_source_bytes_invalidate_verification(self):
        self.external_verify(QP)
        s = self.find("sources", "source_id", QP)
        Path(s["artifact_reference"]).write_text("changed", encoding="utf-8")
        self.invalid("Source artifact bytes changed")

    def test_changed_locator_invalidates_verification(self):
        self.external_verify(QP)
        self.find("locators", "locator_id", "LOC-QP-Q2-a")["label"] = "invented location"
        self.invalid("Locator verification content mismatch")

    def test_changed_source_type_invalidates_trust(self):
        self.external_verify(QP)
        self.find("sources", "source_id", QP)["source_type"] = "official_syllabus"
        self.invalid("Untrusted source verification")

    def test_quotation_requires_verified_text(self):
        self.data["evidence"][0]["content_kind"] = "quotation"
        self.invalid("Quotation needs verified")
        self.external_verify(QP)
        self.invalid("Quotation differs")
        self.data["evidence"][0]["observation"] = "Example verified text."
        validate_document(self.data, self.trust)

    def test_empty_selection_not_vacuously_verified(self):
        self.assertFalse(validation_report(self.data, selected_targets=[])["source_verified"])

    def test_no_fake_registry_promotion(self):
        self.data["competencies"][0]["status"] = "approved"
        self.invalid("Registry state requires trusted decision")

    def test_no_self_approved_relation(self):
        self.mapping().update(review_status="approved", review_decision_id="FAKE")
        self.invalid("Reviewed record needs")

    def test_payload_decision_not_external_trust(self):
        self.approve(self.mapping(), ref("part_mapping", self.mapping()["mapping_id"]))
        self.trust.decisions.clear()
        self.invalid("Untrusted human review")

    def test_approval_requires_supporting_sources(self):
        self.approve(self.mapping(), ref("part_mapping", self.mapping()["mapping_id"]))
        self.invalid("Approved relation requires verified supporting evidence")

    def test_trusted_approval_and_stale_content(self):
        self.external_verify(QP); self.external_verify(MS)
        self.approve(self.mapping(), ref("part_mapping", self.mapping()["mapping_id"]))
        validate_document(self.data, self.trust)
        self.mapping()["rationale"] = "Changed claim"
        self.invalid("Stale review content")

    def test_registry_approval_is_separate_from_gold(self):
        c = self.data["competencies"][0]
        self.approve(c, ref("competency", c["canonical_id"]), registry=True)
        model = validate_document(self.data, self.trust)
        self.assertEqual(sum(c.status == "approved" for c in model.competencies), 1)

    def test_conflicting_active_decisions_rejected(self):
        d = self.approve(self.data["concepts"][0], ref("concept", self.data["concepts"][0]["concept_id"]))
        duplicate = {**d, "decision_id": "REVIEW-OTHER", "decision_source_reference": "test-other"}
        self.data["review_decisions"].append(duplicate)
        self.trust.decisions["test-other"] = digest(duplicate)
        self.invalid("Duplicate active review target")

    def test_not_observed_requires_sample(self):
        self.data["evidence"][0]["observation_status"] = "not_observed"
        self.invalid("explicit examined sample")

    def test_absence_cannot_be_exclusion(self):
        e = self.data["evidence"][0]
        e.update(observation_status="not_observed", examined_sample="Only Q2(a)", explicit_exclusion=True, application="X")
        self.invalid("Exclusion needs an observed")

    def test_scope_and_objective_structural_path(self):
        self.add_scope()
        validate_document(self.data)
        self.data["scopes"][0]["context_id"] = "WRONG"
        self.invalid("Objective/context mismatch")

    def test_official_wording_not_invented(self):
        self.add_scope()
        self.data["objective_references"][0]["wording_excerpt"] = "invented"
        self.invalid("Official wording requires verified")

    def test_explicit_reviewed_exclusion_happy_path(self):
        self.add_exclusion()
        validate_document(self.data, self.trust)

    def test_exclusion_cannot_also_be_included(self):
        scope, _, _ = self.add_exclusion()
        scope["included_applications"] = ["X"]
        self.invalid("also included/unresolved")

    def test_paper_cannot_support_curriculum_exclusion(self):
        _, e, _ = self.add_exclusion()
        self.external_verify(MS)
        e["source_locator_ids"] = ["LOC-MS-Q2-a"]
        for d in self.data["review_decisions"]:
            d["target_content_digest"] = review_content_digest(self.data, d["target"])
            self.trust.decisions[d["decision_source_reference"]] = digest(d)
        self.invalid("reviewed explicit official scope evidence")

    def test_difficulty_measurement_constraints(self):
        self.assertEqual(self.data["question_difficulties"], [])
        base = {"part_id": part_id("Q2-a"), "predicted_difficulty": 0.4, "difficulty_method": "expert_estimate", "provenance": prov()}
        self.data["question_difficulties"] = [base]
        validate_document(self.data)
        for change in ({"predicted_difficulty": True}, {"predicted_difficulty": 1.1},
                       {"observed_difficulty": 0.3}, {"observed_sample_size": 20}, {"reasoning_steps": -1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_document({**self.data, "question_difficulties": [{**base, **change}]})

    def test_difficulty_duplicate_and_container_rejected(self):
        d = {"part_id": part_id("Q2-a"), "provenance": prov()}
        self.data["question_difficulties"] = [d, copy.deepcopy(d)]
        self.invalid("Duplicate part difficulty")
        self.data["question_difficulties"] = [{**d, "part_id": part_id("Q4-c")}]
        self.invalid("Container cannot carry")

    def test_model_copy_does_not_bypass_checks(self):
        model = validate_document(self.data)
        model.part_mappings[0] = model.part_mappings[0].model_copy(update={"canonical_id": "NO-SUCH-COMPETENCY"})
        with self.assertRaisesRegex(ValueError, "Unknown competency"):
            validate_document(model)

    def test_synthetic_source_cannot_claim_verified(self):
        self.data["sources"][0].update(origin="synthetic", synthetic_notice=SYNTHETIC_NOTICE, verification_status="verified")
        self.invalid("Synthetic source needs notice")

    def test_real_provenance_cannot_cite_synthetic_discussion(self):
        self.find("sources", "source_id", "SRC-GOLD-DISCUSSION").update(origin="synthetic", synthetic_notice=SYNTHETIC_NOTICE)
        self.invalid("Real provenance cannot cite")

    def test_evidence_duplicate_and_unknown_reference(self):
        self.mapping()["evidence_ids"].append(self.mapping()["evidence_ids"][0])
        self.invalid("Duplicate evidence references")
        self.data = copy.deepcopy(self.base)
        self.mapping()["evidence_ids"] = ["MISSING"]
        self.invalid("Unknown evidence")

    def test_referenced_evidence_change_invalidates_mapping_review(self):
        self.external_verify(QP); self.external_verify(MS)
        self.approve(self.mapping(), ref("part_mapping", self.mapping()["mapping_id"]))
        self.data["evidence"][0]["observation"] = "A different interpretation under the same evidence ID"
        self.invalid("Stale review content")

    def test_action_classification_has_independent_review(self):
        self.data["competencies"][0]["action_classification"] = {
            "value": "calculation", "rationale": "Test-only classification proposal", "provenance": prov()}
        self.data = AcademicKnowledgePrototype.model_validate(self.data).model_dump()
        classification = self.data["competencies"][0]["action_classification"]
        self.approve(classification, ref("action_classification", "CAN-STAT-MEAN-CALC"))
        model = validate_document(self.data, self.trust)
        self.assertEqual(model.competencies[0].status, "draft")
        classification["value"] = "interpretation"
        self.invalid("Stale review content")

    def test_preserved_project_files(self):
        manifest = json.loads((Path(__file__).parent / "output/academic_knowledge_v03/stable_baseline_sha256.json").read_text(encoding="utf-8"))
        root = Path(manifest["project_root"])
        for relative, expected in manifest["files"].items():
            with self.subTest(file=relative):
                self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
