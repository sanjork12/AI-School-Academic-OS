"""Service-level workflow. Reviewer credentials belong to a trusted human-review caller.

No reviewer keys are provisioned by default. Never give review credentials to a
model/provider or accept them from proposal JSON. HMAC authenticates a configured
review channel, not the quality or biological identity of a reviewer.
"""
import hmac
import hashlib
import re
from datetime import datetime, timezone
from academic_os.curriculum_ingestion.service import serial, Storage
from academic_os.governed_pedagogy.policy import catalog_evidence
from .models import Brief, Proposal, Review, ReviewReceipt, Pack
from .validation import (hash_of, validate_brief, validate_proposal, COMPONENTS,
                         PROHIBITIONS, CONSTRAINTS, REVIEWS)

def signature(review, key):
    return hmac.new(key, serial(review), hashlib.sha256).hexdigest()

class PedagogicalEvidenceService:
    def __init__(self, learning_service, root, *, reviewer_keys=None, domain='HUMAN_REVIEW'):
        if domain not in ('HUMAN_REVIEW', 'SYNTHETIC_TEST_ONLY'): raise ValueError('INVALID_DOMAIN')
        self.learning = learning_service
        self.storage = Storage(root)
        self.domain = domain
        self._reviewer_keys = dict(reviewer_keys or {})
        if any(not isinstance(k, bytes) or len(k) < 32 for k in self._reviewer_keys.values()):
            raise ValueError('REVIEW_KEY_TOO_SHORT')

    def build_pedagogical_authoring_brief(self, learning_spec):
        b = Brief(learning_spec_hash=hash_of(learning_spec), source_learning_spec=learning_spec,
            allowed_categories=COMPONENTS, role_evidence_hash=hash_of(catalog_evidence()),
            prohibited_claims=PROHIBITIONS, authoring_constraints=CONSTRAINTS, review_requirements=REVIEWS)
        return validate_brief(b, self.learning)

    def validate_pedagogical_proposal(self, proposal, brief):
        return validate_proposal(proposal, brief, self.learning)

    def _validated(self, value):
        p = Proposal.model_validate(value)
        result = self.validate_pedagogical_proposal(p, p.brief)
        if not result['valid']: raise ValueError('PROPOSAL_INVALID: ' + '; '.join(result['errors']))
        return p

    def present_for_review(self, proposal):
        p = self._validated(proposal); identity = hash_of(p)
        path = (identity, 'proposal.json')
        if self.storage.safe(*path).exists():
            if self.storage.read(*path) != serial(p): raise ValueError('STORED_PROPOSAL_CHANGED')
        else: self.storage.write(path, serial(p))
        return dict(proposal_hash=identity, proposal=p.model_dump(mode='json'), status='AWAITING_HUMAN_REVIEW',
            components=COMPONENTS, warnings=[w.model_dump(mode='json') for w in p.brief.source_learning_spec.warnings])

    def _authenticate(self, review, supplied_signature):
        key = self._reviewer_keys.get(review.reviewer_id)
        if review.domain != self.domain or key is None or not hmac.compare_digest(signature(review,key), supplied_signature):
            raise ValueError('UNAUTHENTICATED_REVIEW')
        if [d.component for d in review.decisions] != COMPONENTS: raise ValueError('REVIEW_COMPONENTS_INCOMPLETE_OR_UNORDERED')

    def record_pedagogical_review(self, proposal, decision, *, reviewer_signature):
        p = self._validated(proposal); r = Review.model_validate(decision)
        self._authenticate(r, reviewer_signature)
        if r.proposal_hash != hash_of(p): raise ValueError('REVIEW_PROPOSAL_HASH_MISMATCH')
        if self.domain == 'HUMAN_REVIEW' and p.pedagogical_adapter.evidence_basis.origin == 'SYNTHETIC_OFFLINE':
            raise ValueError('SYNTHETIC_FIXTURE_CANNOT_RECEIVE_REAL_APPROVAL')
        self.present_for_review(p)
        rid = hash_of(r); path = (hash_of(p), rid + '.review.json')
        if self.storage.safe(*path).exists():
            receipt = ReviewReceipt.model_validate_json(self.storage.read(*path))
            self._verify_receipt(p, receipt)
            return receipt
        receipt = ReviewReceipt(review=r, semantic_hash=rid, recorded_at=datetime.now(timezone.utc).isoformat(), signature=reviewer_signature)
        self.storage.write(path, serial(receipt))
        return receipt

    def _verify_receipt(self, p, receipt):
        r = receipt.review; self._authenticate(r, receipt.signature)
        if r.proposal_hash != hash_of(p) or receipt.semantic_hash != hash_of(r): raise ValueError('REVIEW_HASH_MISMATCH')
        if self.domain == 'HUMAN_REVIEW' and p.pedagogical_adapter.evidence_basis.origin == 'SYNTHETIC_OFFLINE': raise ValueError('SYNTHETIC_REVIEW_FORBIDDEN')
        if self.storage.read(hash_of(p), receipt.semantic_hash + '.review.json') != serial(receipt): raise ValueError('RECEIPT_NOT_RECORDED_OR_CHANGED')
        if self.storage.read(hash_of(p), 'proposal.json') != serial(p): raise ValueError('REVIEWED_PROPOSAL_CHANGED')

    def build_approved_pedagogical_evidence_pack(self, proposal, review):
        p = self._validated(proposal); receipt = ReviewReceipt.model_validate(review)
        self._verify_receipt(p, receipt)
        if any(d.decision != 'APPROVE' for d in receipt.review.decisions): raise ValueError('ALL_COMPONENT_APPROVAL_REQUIRED')
        identity = hash_of(dict(proposal_hash=hash_of(p), semantic_review_hash=receipt.semantic_hash))
        return Pack(proposal=p, review_receipt=receipt, evidence_identity=identity)

    def validate_pedagogical_evidence_pack(self, value):
        # Revalidate every binding and receipt independently; do not trust old validation results.
        try:
            pack = Pack.model_validate(value); p = self._validated(pack.proposal)
            self._verify_receipt(p, pack.review_receipt)
            if any(d.decision != 'APPROVE' for d in pack.review_receipt.review.decisions): raise ValueError('COMPONENT_NOT_APPROVED')
            expected = hash_of(dict(proposal_hash=hash_of(p), semantic_review_hash=pack.review_receipt.semantic_hash))
            if pack.evidence_identity != expected: raise ValueError('PACK_IDENTITY_CHANGED')
            return dict(valid=True, evidence_identity=expected, domain=self.domain, trusted_state_changed=False)
        except (ValueError, OSError) as exc:
            return dict(valid=False, errors=[str(exc)])

    def persist_evidence_pack(self, pack):
        result = self.validate_pedagogical_evidence_pack(pack)
        if not result['valid']: raise ValueError('INVALID_EVIDENCE_PACK')
        p = Pack.model_validate(pack); path = ('packs', p.evidence_identity + '.json')
        if self.storage.safe(*path).exists():
            if self.storage.read(*path) != serial(p): raise ValueError('PACK_ALREADY_EXISTS_WITH_DIFFERENT_RECEIPT')
        else: self.storage.write(path, serial(p))
        return p.evidence_identity

    def read_evidence_pack(self, identity):
        if not re.fullmatch('[a-f0-9]{64}', identity): raise ValueError('INVALID_IDENTITY')
        pack = Pack.model_validate_json(self.storage.read('packs', identity + '.json'))
        if pack.evidence_identity != identity or not self.validate_pedagogical_evidence_pack(pack)['valid']:
            raise ValueError('STORED_PACK_INVALID')
        return pack
