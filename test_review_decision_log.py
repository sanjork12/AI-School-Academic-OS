import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical_schema import CanonicalReviewDecision
from review_decision_log import append_review_decisions


def decision(identifier):
    return CanonicalReviewDecision(
        decision_id=identifier, proposal_type="mapping", decision="approve",
        approved_canonical_id="CAN-TEST", approved_subject_domain="Algebra",
        approved_skill_name="Test skill",
    ).model_dump()


class DecisionLogTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "decisions.json"
        self.a, self.b, self.c = [decision(x) for x in ["A", "B", "C"]]

    def save(self, records):
        data = {"prototype_version": "0.2", "decision_count": len(records),
                "audit_note": "preserve", "decisions": records}
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return self.path.read_bytes()

    def merge(self, records):
        with contextlib.redirect_stdout(io.StringIO()) as report:
            result = append_review_decisions(self.path, records)
        self.report = report.getvalue()
        return result

    def test_create_and_atomic_write(self):
        result = self.merge([self.a])
        self.assertEqual(json.loads(self.path.read_text()), result)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])
        self.assertIn("ADD decision: A", self.report)

    def test_append_preserves_order_and_metadata(self):
        self.save([self.a, self.b])
        result = self.merge([self.b, self.c])
        self.assertEqual(result["decisions"], [self.a, self.b, self.c])
        self.assertEqual(result["decision_count"], 3)
        self.assertEqual(result["audit_note"], "preserve")
        self.assertEqual(result["prototype_version"], "0.2")
        self.assertIn("SKIP identical decision: B", self.report)
        self.assertIn("ADD decision: C", self.report)

    def test_old_history_and_idempotency(self):
        original = self.save([self.a, self.b, self.c])
        for _ in range(2):
            self.assertEqual(self.merge([self.a, self.b])["decisions"],
                             [self.a, self.b, self.c])
            self.assertEqual(self.path.read_bytes(), original)

    def test_normalized_defaults_and_key_order(self):
        raw = {"decision": "reject", "proposal_type": "mapping", "decision_id": "A"}
        original = self.save([raw])
        candidate = CanonicalReviewDecision.model_validate(raw).model_dump()
        self.merge([dict(reversed(list(candidate.items())))])
        self.assertEqual(self.path.read_bytes(), original)

    def test_conflict_no_partial_append(self):
        original = self.save([self.a])
        changes = {
            "approved_subject_domain": "Geometry", "approved_skill_name": "Other",
            "approved_description": "Other", "approved_canonical_id": "CAN-OTHER",
            "decision": "reject", "source_ids": ["OTHER"],
            "reviewer_notes": "Other", "reviewed_by": "Other",
            "proposal_type": "consolidation",
            "approved_official_mappings": [{
                "official_source_id": "TEST", "canonical_id": "CAN-TEST",
                "relationship": "equivalent", "confidence": 1,
                "mapping_method": "human", "review_status": "approved"}],
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = {**self.a, field: value}
                with self.assertRaisesRegex(ValueError, "Conflicting human review decision: A"):
                    self.merge([self.c, changed])
                self.assertEqual(self.path.read_bytes(), original)

    def test_existing_duplicate(self):
        original = self.save([self.a, self.a])
        with self.assertRaisesRegex(ValueError, "Duplicate decision ID in existing history: A"):
            self.merge([self.c])
        self.assertEqual(self.path.read_bytes(), original)

    def test_candidate_duplicate(self):
        original = self.save([self.a])
        with self.assertRaisesRegex(ValueError, "Duplicate decision ID in candidate decisions: B"):
            self.merge([self.b, self.b])
        self.assertEqual(self.path.read_bytes(), original)

    def test_schema_and_mapping_safety(self):
        mapping = {"official_source_id": "TEST", "canonical_id": "CAN-TEST",
                   "relationship": "equivalent", "confidence": 1,
                   "mapping_method": "human", "review_status": "approved"}
        invalid = [
            {**self.a, "decision": "invalid"},
            {**self.a, "approved_canonical_id": None},
            *[{**self.a, "approved_official_mappings": [{**mapping, **change}]}
              for change in [{"canonical_id": "OTHER"}, {"review_status": "pending"}]],
        ]
        for record in invalid:
            for existing in [True, False]:
                original = self.save([record] if existing else [])
                with self.assertRaises(ValueError):
                    self.merge([] if existing else [record])
                self.assertEqual(self.path.read_bytes(), original)

    def test_extra_audit_fields_preserved_and_compared(self):
        record = {**self.a, "audit": {"note": "keep"}}
        self.save([record])
        result = self.merge([record, self.b])
        self.assertEqual(result["decisions"][0], record)
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.merge([self.a])
        self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_history_not_replaced(self):
        for text in ['{', '{}', '[]', '{"decisions": null}']:
            self.path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.merge([self.a])
            self.assertEqual(self.path.read_text(), text)

    def test_atomic_replace_failure_preserves_history(self):
        original = self.save([self.a])
        with patch.object(Path, "replace", side_effect=OSError("test failure")):
            with self.assertRaises(OSError):
                self.merge([self.b])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])


if __name__ == "__main__":
    unittest.main()
