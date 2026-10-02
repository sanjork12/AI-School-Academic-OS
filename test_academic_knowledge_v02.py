"""Semantic and failure-path regression tests; all mutations are in memory."""

import copy
import hashlib
import json
import unittest

from academic_knowledge_schema_v02 import (
    CanonicalCompetency, CurriculumScope, QuestionDifficulty,
)
from build_academic_knowledge_v02_prototype import (
    MATRIX_CONTEXT, MATRIX_OBJECTIVE, REGION, VECTOR, build_prototype, synthetic,
)
from validate_academic_knowledge_v02 import ROOT, DEFAULT_FILE, validate_document


class AcademicKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prototype = build_prototype().model_dump()

    def setUp(self):
        self.data = copy.deepcopy(self.prototype)

    def invalid(self, pattern=None):
        with self.assertRaisesRegex(ValueError, pattern or "."):
            validate_document(self.data)

    def records(self, collection, canonical_id):
        return [r for r in self.data[collection] if r.get("canonical_id") == canonical_id]

    def test_same_competency_across_contexts_and_stages(self):
        mappings = self.records("mappings", VECTOR)
        self.assertEqual(len(mappings), 2)
        contexts = [c for c in self.data["contexts"] if c["context_id"] in
                    {m["context_id"] for m in mappings}]
        self.assertEqual(len({c["educational_stage"] for c in contexts}), 2)
        self.assertEqual(len(self.records("competencies", VECTOR)), 1)
        self.assertTrue(all(c["tier"] is None and c["pathway"] is None for c in contexts))

    def test_same_competency_different_scopes(self):
        scopes = self.records("scopes", VECTOR)
        self.assertNotEqual(scopes[0]["constraints"], scopes[1]["constraints"])
        self.assertIn("2D vectors", scopes[0]["constraints"])
        self.assertIn("2D and 3D vectors", scopes[1]["constraints"])

    def test_context_and_stage_cannot_be_canonical_fields(self):
        for field in ("exam_board", "qualification", "tier", "educational_stage", "curriculum_version"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                CanonicalCompetency.model_validate({**self.data["competencies"][0], field: "Higher"})

    def test_tier_change_does_not_create_skill(self):
        self.data["contexts"][2]["tier"] = "Any local tier label"
        result = validate_document(self.data)
        self.assertEqual(len(result.competencies), len(self.prototype["competencies"]))

    def test_partial_curriculum_overlap_is_representable(self):
        extra = copy.deepcopy(self.records("mappings", VECTOR)[1])
        extra["canonical_id"] = "CAN-MATH-MATRIX-ADD"
        extra["relationship"] = "partial"
        extra["evidence_ids"] = []
        self.data["mappings"].append(extra)
        validate_document(self.data)
        skills = [{m["canonical_id"] for m in self.data["mappings"] if
                   m["context_id"] == f"SYN-CTX-VECTOR-{label}"} for label in ("A", "B")]
        self.assertEqual(skills[0] & skills[1], {VECTOR})
        self.assertEqual(skills[1] - skills[0], {"CAN-MATH-MATRIX-ADD"})

    def test_question_difficulty_is_independent(self):
        self.assertEqual({m["canonical_id"] for m in self.data["question_mappings"]}, {VECTOR})
        self.assertEqual(len({q["curriculum_context_id"] for q in self.data["questions"]}), 1)
        self.assertEqual(len({d["predicted_difficulty"] for d in self.data["question_difficulties"]}), 2)
        self.assertIsNone(self.data["question_difficulties"][0]["observed_difficulty"])
        for model in (CanonicalCompetency, CurriculumScope):
            self.assertNotIn("difficulty_level", model.model_fields)

    def test_tiers_stages_invalid_as_difficulty(self):
        for field in ("predicted_difficulty", "observed_difficulty", "scale"):
            for value in ("Foundation", "Higher", "A-Level", "IGCSE"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    QuestionDifficulty.model_validate({**self.data["question_difficulties"][0], field: value})

    def test_difficulty_measurement_constraints(self):
        for change in ({"predicted_difficulty": 1.1}, {"reasoning_steps": -1},
                       {"observed_difficulty": 0.5}, {"observed_sample_size": 10},
                       {"predicted_difficulty": True}, {"difficulty_method": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                QuestionDifficulty.model_validate({**self.data["question_difficulties"][0], **change})

    def test_supporting_evidence_linked_to_mapping(self):
        evidence = {e["evidence_id"]: e for e in self.data["evidence"]}
        for mapping in self.records("mappings", REGION):
            self.assertTrue(any(evidence[i]["evidence_role"] == "supports" for i in mapping["evidence_ids"]))

    def test_clarification_can_reference_scope(self):
        for scope in self.records("scopes", REGION):
            evidence = next(e for e in self.data["evidence"] if e["evidence_id"] == scope["evidence_ids"][0])
            self.assertEqual(evidence["scope_id"], scope["scope_id"])
            self.assertEqual(evidence["evidence_role"], "clarifies")

    def test_inverse_not_observed_stays_unresolved(self):
        inverse = "CAN-MATH-MATRIX-INVERSE"
        scope = self.records("scopes", inverse)[0]
        self.assertTrue(scope["unresolved_scope"])
        self.assertEqual(scope["excluded_applications"], [])
        self.assertEqual(self.records("mappings", inverse), [])
        self.assertEqual(self.records("evidence", inverse)[0]["observation_status"], "not_observed")
        self.assertEqual(validate_document(self.data).model_dump(), self.data)

    def add_exclusion(self):
        scope = self.records("scopes", "CAN-MATH-MATRIX-INVERSE")[0]
        scope["excluded_applications"] = [{
            "application": "Find an inverse matrix", "evidence_ids": ["SYN-EV-MATRIX-INVERSE"],
            "rationale": "Test exclusion claim", "review_status": "approved",
        }]

    def test_absence_cannot_support_exclusion(self):
        self.add_exclusion()
        self.invalid("NOT OBSERVED")

    def test_absence_cannot_be_relabeled_explicit_exclusion(self):
        self.records("evidence", "CAN-MATH-MATRIX-INVERSE")[0]["explicit_exclusion"] = True
        self.invalid("Explicit exclusion")

    def test_exclusion_needs_official_reviewed_explicit_evidence(self):
        self.add_exclusion()
        e = self.records("evidence", "CAN-MATH-MATRIX-INVERSE")[0]
        e.update(observation_status="observed", evidence_role="supports", explicit_exclusion=True,
                 source_type="official_specification_note", authority="official_requirement",
                 review_status="approved", observation="Synthetic explicit exclusion for a validator test.")
        validate_document(self.data)
        e["review_status"] = "pending"
        self.invalid("Exclusion needs")

    def test_textbook_does_not_override_official_requirement(self):
        self.add_exclusion()
        e = self.records("evidence", "CAN-MATH-MATRIX-INVERSE")[0]
        e.update(observation_status="observed", evidence_role="supports", explicit_exclusion=True,
                 source_type="third_party_textbook", authority="third_party_material",
                 review_status="approved")
        self.invalid("Exclusion needs")

    def test_ambiguous_and_insufficient_evidence_can_remain_unresolved(self):
        broad = next(e for e in self.data["evidence"] if e["evidence_id"] == "SYN-EV-MATRIX-AMBIGUOUS")
        self.assertEqual(broad["observation_status"], "ambiguous")
        broad["observation_status"] = "insufficient_evidence"
        validate_document(self.data)
        self.assertTrue(all(s["unresolved_scope"] for s in self.data["scopes"] if s["context_id"] == MATRIX_CONTEXT))

    def test_one_broad_objective_can_map_multiple_skills(self):
        mappings = [m for m in self.data["mappings"] if m["official_source_id"] == MATRIX_OBJECTIVE]
        self.assertEqual(len({m["canonical_id"] for m in mappings}), 4)
        self.assertTrue(all(m["relationship"] == "broader" and m["review_status"] == "pending" for m in mappings))

    def test_invalid_evidence_reference(self):
        self.data["mappings"][0]["evidence_ids"] = ["MISSING"]
        self.invalid("Unknown evidence reference")

    def test_invalid_canonical_reference(self):
        self.data["mappings"][0]["canonical_id"] = "MISSING"
        self.invalid("Unknown canonical reference")

    def test_invalid_context_reference(self):
        self.data["objective_references"][0]["context_id"] = "MISSING"
        self.invalid("Unknown context")

    def test_invalid_scope_reference(self):
        self.data["evidence"][0]["scope_id"] = "MISSING"
        self.invalid("Unknown scope reference")

    def test_wrong_but_existing_evidence_target(self):
        self.data["mappings"][0]["evidence_ids"] = self.data["mappings"][1]["evidence_ids"]
        self.invalid("Evidence objective/context mismatch")

    def test_duplicate_ids_and_pairs(self):
        for collection in ("contexts", "competencies", "objective_references", "scopes", "evidence",
                           "mappings", "questions", "question_mappings", "question_difficulties"):
            with self.subTest(collection=collection):
                self.data = copy.deepcopy(self.prototype)
                self.data[collection].append(copy.deepcopy(self.data[collection][0]))
                self.invalid("Duplicate")

    def test_enum_values_and_authority_spoofing(self):
        for field, value in (("source_type", "blog"), ("authority", "trusted"),
                             ("review_status", "automatic"), ("observation_status", "excluded"),
                             ("evidence_role", "maybe"), ("confidence", 2.0)):
            with self.subTest(field=field):
                self.data = copy.deepcopy(self.prototype)
                self.data["evidence"][0][field] = value
                self.invalid()
        self.data = copy.deepcopy(self.prototype)
        self.data["evidence"][-1]["authority"] = "official_requirement"
        self.invalid("authority/source mismatch")

    def test_synthetic_cannot_masquerade_as_real(self):
        for collection, index in (("contexts", 2), ("competencies", 1),
                                  ("objective_references", 2), ("evidence", 4), ("questions", 0)):
            with self.subTest(collection=collection):
                self.data = copy.deepcopy(self.prototype)
                p = self.data[collection][index]["provenance"]
                p.update(origin="real", synthetic_notice=None, source_reference="fake-official.json")
                self.invalid()

    def test_synthetic_notice_required(self):
        self.data["contexts"][2]["provenance"]["synthetic_notice"] = None
        self.invalid("Synthetic data requires")

    def test_real_record_cannot_be_marked_synthetic(self):
        self.data["objective_references"][0]["provenance"] = synthetic("fake-relabel")
        self.invalid("origin mismatch")

    def test_unknown_official_objective_rejected(self):
        self.data["objective_references"][0]["official_source_id"] = "EDX-4MA1-F-FAKE"
        self.invalid("Unknown real official ID")

    def test_real_wording_and_context_must_match_source(self):
        self.data["objective_references"][0]["wording_excerpt"] = "Invented official wording"
        self.invalid("wording must match")
        self.data = copy.deepcopy(self.prototype)
        self.data["contexts"][0]["tier"] = "Higher"
        self.invalid("tier mismatch")

    def test_unknown_question_and_difficulty_references(self):
        for collection, field in (("question_mappings", "question_id"),
                                  ("question_mappings", "canonical_id"),
                                  ("question_difficulties", "question_id"),
                                  ("questions", "curriculum_context_id")):
            with self.subTest(collection=collection, field=field):
                self.data = copy.deepcopy(self.prototype)
                self.data[collection][0][field] = "MISSING"
                self.invalid("Unknown")

    def test_real_edexcel_shared_skill_distinct_scope(self):
        mappings = self.records("mappings", REGION)
        self.assertEqual({m["official_source_id"] for m in mappings},
                         {"EDX-4MA1-F-2.8-E", "EDX-4MA1-H-2.8-B"})
        scopes = self.records("scopes", REGION)
        self.assertNotEqual(scopes[0]["constraints"], scopes[1]["constraints"])
        self.assertEqual({self.data["contexts"][i]["tier"] for i in (0, 1)}, {"Foundation", "Higher"})
        self.assertTrue(all(m["human_review_decision_id"] == "REV-4MA1-T2-INEQ-REGION-001" for m in mappings))

    def test_builder_deterministic_and_matches_saved_artifact(self):
        self.assertEqual(build_prototype().model_dump(), self.prototype)
        self.assertEqual(json.loads(DEFAULT_FILE.read_text(encoding="utf-8")), self.prototype)

    def test_v01_files_remain_unchanged(self):
        # Pinned at the start of v0.2 work; update deliberately if v0.1 later evolves.
        for name, expected in V01_SHA256.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


# Populated from the pre-change baseline, excluding .env, .venv and build caches.
V01_SHA256 = {
    "add_source_ids.py": "33047c8ee001f98535c65ac62c92523568f1b39e860079e228664961ab222580",
    "ai_canonical_mapper.py": "a227ebf6260e2a9ac10d9e88d6cdd3f0085c11038fe2ac54a21b6f5efba704ef",
    "build_canonical_prototype.py": "a112522aae0214876fcf12005f24a38349349d21f5dcf3cf484b45c00dd17e6c",
    "build_review_decisions_prototype.py": "c5ddda15cd03261b57fede29db0e63a9338e480d870d5c2b267ac1a1e516fce3",
    "build_scope_metadata_prototype.py": "236d0bd2a4a06cbd42a9e81b12deeab41cb02386a0ccff797fec522e7f0ef6fd",
    "canonical_schema.py": "779e9fc6eccda8849bb29142638a58721b914cb8b7c254a417485226933a064c",
    "consolidate_canonical_proposals.py": "5e8c174133ffb6bed00ad8e704294c71d33505858fd686071bdb9f5474d285c7",
    "curriculum_schema.py": "f9d6c0326ea22dd953798bec3927f65cd306f63e19bc6eaffd0e3ce3df1242f1",
    "extract_syllabus.py": "963e1a8ce5f25ba5fbb355174b8fcdad560306e615245ccada1f79561d5a5823",
    "frontend/.gitignore": "6e499bcb864728271c8ebe3f2ef3dd5d0801bd2991e06860f940d0efc3cd0246",
    "frontend/AGENTS.md": "63f2c50380ed6303237cce215ce27af1d620d094c215e28d1b1538a3c070e3bb",
    "frontend/CLAUDE.md": "336cc4fbf19beaada7ccf9986414fa91851a8d7a07dfb3ccbe800a69eed0ab49",
    "frontend/README.md": "cec3d130ed39181c76938c42e2dd8a82a284cf81cabe5588c42acb0dd5b9e26e",
    "frontend/eslint.config.mjs": "c9cc08711ec1cd6a33645796797ad293ada9991c2a45e8f416613c5539976eeb",
    "frontend/next-env.d.ts": "1b59d4c6b83807db275d43f3cf2cc8e9323f465fab764eea091cc5becd5bad37",
    "frontend/next.config.ts": "81d6d82fa0743fb0db8e6258432c6c63dd4201ada8b413cec345cca27add2cd0",
    "frontend/package-lock.json": "468d45551d9efafd7d1eb55f84c8d74b5bdb59ae707dda34890f88bcf333a24b",
    "frontend/package.json": "8271ff31626d8f977bf39bad115837dd7bae7148f787f19db4b696ac8d5463ad",
    "frontend/playwright.config.ts": "85217114dcd1ab5ca6cef4fa264cdb53e130a0f54cef103027dc23709b0b163b",
    "frontend/postcss.config.mjs": "b783348d5618047d0f37e12acd15c5a2c5f02809d8711e0764c9cea52750346c",
    "frontend/scripts/prepare-demo.mjs": "00ab288b5b656b71637314d7b141ef203f4da0f7bda1b36d6f2499b0cc01a7c1",
    "frontend/scripts/serve-static.mjs": "548cadb824ee5f721774e6c077a1de73def65eb1e5d316c7b87d072cc9a785d8",
    "frontend/src/app/globals.css": "35266744ef981f98b6caa7403dc8037c35fcb5eb320eccec480dfa6e17c6a8bb",
    "frontend/src/app/layout.tsx": "4ea00ad8e197c8bde2034f6a3e6caa8366e6aebab022b2342bf52ba809354612",
    "frontend/src/app/page.tsx": "4303f438932334b360b81f57ee43e5f4705cc2e51f1f1892c935aab452508931",
    "frontend/src/components/approved-graph.tsx": "7fdb032fdbda4ed1c06150fdba770c43aee0a40a73394e5a7e7d88cc7b07c8bc",
    "frontend/src/components/curriculum.tsx": "6d2082e9d04e696ce6329559129e195e752fbbc778b880126485af4dc56c24a6",
    "frontend/src/components/import-processing.tsx": "b72bc37d495c65af003ee96526c211cffb2ae64061b501d7e382a86223bd6c5a",
    "frontend/src/components/review.tsx": "ccddc175e24f43e0a6c35d29d42c5e0d5569b6cabc5a000b95256e7b94ec97fb",
    "frontend/src/components/shared.tsx": "6d81eeed7a5590d912d712c4665b633df085ed1563e49c26e74c34cd7af8c194",
    "frontend/src/components/workspace.tsx": "0a4150c3de5b6860fd83766486073e4a1a24950d4fe85291e2198d4c427bab58",
    "frontend/src/data/demo.json": "feb0ca73516be9c5767809cad8235f1902a7d293bbf6bf99ecd22691188bba85",
    "frontend/src/data/demo.ts": "4a518ecb38d7ea489b2731fbfe5887dbc06aabdbde9c080090c30971d0432286",
    "frontend/src/data/types.ts": "9cee0b3a86aac737a67569f452607c47bb3a5d76b06d9fa18164cc8d1e6d0e2e",
    "frontend/tests/browser/demo.spec.ts": "2a9de61574ad10633a19d94eba98d834b5af2235994c7539afe8fee85fa7e471",
    "frontend/tests/data.test.mjs": "142e2660a2b94a8680976e318240355eb8d1217e51f7b2696b8e5b6a9459ba9a",
    "frontend/tsconfig.json": "20dfd1fd770b589531d826fc3f0e2c1e723d351a389c8602da00686ac1c1f1dc",
    "output/topic2_ai_consolidation_proposals.json": "51c1954ef5cb46df6defbfb460aa9cfc25440a2fb98744342777e96e1a7f9809",
    "output/topic2_ai_mapping_proposals.json": "2376a72def823ec24bd8d632188476d47719420faa07dbdb82fc40d09fc2bc2e",
    "output/topic2_canonical_promoted.json": "d985939077a85c8828ee6c45d421a646a6af8b24a46dcd72b377b3120ad600d2",
    "output/topic2_canonical_prototype.json": "b417fb173a41a446ceba821abf8e94938ac192eec8ec37981022862c727beded",
    "output/topic2_foundation_parsed.json": "4ab060395b4893a65c5d1560518dd154888cd4899c64e1b13a5f571b09941d95",
    "output/topic2_higher_parsed.json": "0e8b9566fb97519ad1e1019faa5a2ec47a96ce68c194f483e91aa25bebc00d10",
    "output/topic2_human_review_decisions.json": "05a8a3c8035acdc40f6242dfb9a9d6c9b9bf18858d9fe67bd79f22a7d7ff08f9",
    "output/topic2_scope_metadata_prototype.json": "a5acfb0fbe54e0d5ca929d25976cb2e1dd5f6aa0e1788cace6b52e7d3b61d5b0",
    "parse_curriculum.py": "0095ce99f29aa579377663a2ea4dce1de486bfffbecaf44b18dcbfd58a325287",
    "promote_review_decisions.py": "def7d31eb2774645a1fe0e334e583f57dbfc88dfb3e658d086918d6017e88055",
    "review_decision_log.py": "a0702b75ce792737a73f4e8a55713fb2283760b6a37f4fb35fa812f65b3569da",
    "test_review_decision_log.py": "e568872fdbe399aff53f6ef2d50aa92dca88905618a17423cca97771643a3123",
    "validate_canonical.py": "c4d3b499fc1658e09f05add201de5b34b964326551858ea3a5888f92c5aba9fa",
    "validate_curriculum.py": "ac96e8949b3cb412a3205aebae8330c03f585761c209fe39f25291c1d1f1336a",
    "validate_scope_metadata.py": "a00cb96b654cf0d4fa712ccd13b3627abce49cd53d9d2355c10810e5b70ff146"
}


if __name__ == "__main__":
    unittest.main()
