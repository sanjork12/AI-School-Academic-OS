"""Validate current learning evidence and persist a qualification, never fill gaps."""
import json
import re
import threading
from pydantic import ValidationError
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import serial, Storage, now
from academic_os.governed_learning.models import GovernedLearningSpecification
from .models import (PedagogicalSpecificationEligibility, LessonAuthoringEligibility,
                     Qualification, Governance)
from .policy import VERSION, POLICY_HASH, AUTHORING_VERSION, evaluate_verified, authoring_without_spec
from .validation import validate_qualification_bound, validate_spec_bound, report
from .consumer import consume, validate_consumed
from .policy import evaluate_with_approved
from .models import GovernedPedagogicalSpecification
from . import authoring


def reject(code, message): raise core.IngestionError(code, message)


class GovernedPedagogyService:
    def __init__(self, learning_service, root=None, *, evidence_service=None):
        self.learning = learning_service
        self.evidence_service = evidence_service
        self.storage = Storage(root or learning_service.capabilities.ingestion.storage.safe('runs', 'governed-pedagogy'))
        self.lock = threading.RLock()

    def evaluate_pedagogical_spec_eligibility(self, supplied, expected_learning_hash=None, *, approved_pack=None):
        raw = supplied.model_dump(mode='json') if hasattr(supplied, 'model_dump') else supplied
        digest = core.digest(serial(raw))
        try:
            if not isinstance(raw, dict) or raw.get('schema_version') != 'governed-learning-specification/1':
                reject('UNSUPPORTED_LEARNING_SCHEMA', 'Unsupported Learning Specification contract.')
            spec = GovernedLearningSpecification.model_validate(raw); digest = core.digest(serial(spec))
            if expected_learning_hash is not None and digest != expected_learning_hash:
                reject('STALE_LEARNING_HASH', 'Learning specification hash differs.')
            if not self.learning.validate_learning_spec(spec).valid:
                reject('LEARNING_SPEC_INVALID', 'Learning specification does not match current bound evidence.')
            if approved_pack is not None:
                consumed=consume(spec,approved_pack,self.evidence_service)
                validate_consumed(consumed,spec,self.evidence_service)
                return evaluate_with_approved(spec,consumed)
            return evaluate_verified(spec)
        except (core.IngestionError, ValueError, FileNotFoundError, KeyError) as exc:
            code = exc.code if isinstance(exc, core.IngestionError) else 'LEARNING_EVIDENCE_INVALID'
            return PedagogicalSpecificationEligibility(policy_version=VERSION, policy_sha256=POLICY_HASH,
                learning_spec_hash=digest, selected_target_id=None, status='UNSUPPORTED' if code.startswith('UNSUPPORTED') else 'BLOCKED',
                reason_codes=[code], missing_requirements=['VALID_SOURCE_BOUND_LEARNING_SPEC_REQUIRED'],
                requirements=[], warnings=[], evidence_refs={}, actions=[], role_contract=None, binding_valid=False)

    def build_pedagogical_spec(self, learning_spec, eligibility, *, approved_pack=None):
        current = self.evaluate_pedagogical_spec_eligibility(learning_spec,approved_pack=approved_pack)
        try: supplied = PedagogicalSpecificationEligibility.model_validate(eligibility)
        except ValidationError: reject('ELIGIBILITY_EVIDENCE_REQUIRED', 'Valid eligibility evidence is required.')
        if supplied != current: reject('STALE_ELIGIBILITY', 'Eligibility must match current policy and source evidence.')
        if current.status not in ('ELIGIBLE', 'ELIGIBLE_WITH_WARNINGS'):
            reject('PEDAGOGICAL_INPUTS_INCOMPLETE', ', '.join(current.missing_requirements))
        if approved_pack is not None:
            learning_spec=GovernedLearningSpecification.model_validate(learning_spec)
            consumed=consume(learning_spec,approved_pack,self.evidence_service)
            spec=GovernedPedagogicalSpecification(construction_version='governed-approved-pedagogical-construction/1',
                learning_spec_hash=current.learning_spec_hash,source_learning_spec=learning_spec,eligibility=current,
                policy_version=current.policy_version,learning_scope=learning_spec.curriculum_scope,
                instructional_goal_refs=[i.intention_id for i in learning_spec.learning_intentions],teaching_phases=[],
                role_contract=current.role_contract,activity_constraints=current.requirements,warnings=current.warnings,
                governance_state=Governance(),approved_evidence=consumed)
            if not self.validate_pedagogical_spec(spec).valid:reject('CONSTRUCTED_SPEC_INVALID','Independent validation failed.')
            return spec
        # All supported governed-learning/1 records explicitly lack the required inputs.
        # No permissive generic fallback exists; a stronger input/adapter needs a new policy.
        reject('UNSUPPORTED_CONSTRUCTION_ADAPTER', 'No qualified activity/check adapter is registered for this contract version.')

    def validate_pedagogical_spec(self, spec):
        try: return validate_spec_bound(spec, self.learning, self.evidence_service)
        except (core.IngestionError, ValueError, FileNotFoundError, KeyError): return report(spec, ['SOURCE_OR_POLICY_EVIDENCE_CHANGED'])

    def evaluate_lesson_authoring_eligibility(self, spec=None, *, learning_spec=None, scope_framing=None):
        if spec is None:
            if learning_spec is None: reject('LEARNING_INPUT_REQUIRED', 'Supply bound learning evidence for a no-spec authoring decision.')
            return authoring_without_spec(self.evaluate_pedagogical_spec_eligibility(learning_spec))
        validation = self.validate_pedagogical_spec(spec)
        try:
            typed=GovernedPedagogicalSpecification.model_validate(spec)
            if typed.approved_evidence is not None:
                from academic_os.generic_role_authoring.scope import validate_scope_framing
                scope_check=None if scope_framing is None else validate_scope_framing(scope_framing,typed,self)
                return authoring.evaluate(typed,validation,scope_validation=scope_check)
        except ValueError:pass
        raw = spec.model_dump(mode='json') if hasattr(spec, 'model_dump') else spec
        return LessonAuthoringEligibility(status='BLOCKED', reason_codes=['INVALID_OR_UNSUPPORTED_PEDAGOGICAL_SPEC'],
            missing_requirements=['VALID_PEDAGOGICAL_SPEC_REQUIRED', 'EXECUTABLE_ROLE_CONTRACTS_REQUIRED', 'ROLE_SPECIFIC_CONTENT_VALIDATORS_REQUIRED'],
            warnings=[], evidence_refs={}, learning_spec_hash=raw.get('learning_spec_hash', '') if isinstance(raw, dict) else '',
            pedagogical_spec_hash=validation.semantic_sha256, policy_version=AUTHORING_VERSION)

    def validate_pedagogical_eligibility(self, value, learning_spec, *, approved_pack=None):
        from .validation import validate_eligibility_bound
        return validate_eligibility_bound(value,learning_spec,approved_pack,self.learning,self.evidence_service)

    def validate_lesson_authoring_eligibility(self, value, spec, *, scope_framing=None):
        typed=GovernedPedagogicalSpecification.model_validate(spec)
        from academic_os.generic_role_authoring.scope import validate_scope_framing
        scope_check=None if scope_framing is None else validate_scope_framing(scope_framing,typed,self)
        return authoring.validate_gate(value,typed,self.validate_pedagogical_spec(typed),scope_validation=scope_check)

    def persist_pedagogical_spec(self, value):
        spec=GovernedPedagogicalSpecification.model_validate(value)
        validation=self.validate_pedagogical_spec(spec)
        if not validation.valid:reject('PEDAGOGICAL_SPEC_INVALID','Cannot store invalid specification.')
        identity=validation.semantic_sha256
        path=('specifications',identity+'.json')
        with self.lock:
            if self.storage.safe(*path).exists():
                if self.storage.read(*path)!=serial(spec):reject('SPEC_CHANGED','Stored specification differs.')
            else:self.storage.write(path,serial(spec))
        return identity

    def read_constructed_spec(self, identity):
        if not re.fullmatch('[a-f0-9]{64}',identity):reject('NOT_FOUND','Invalid specification identity.')
        spec=GovernedPedagogicalSpecification.model_validate_json(self.storage.read('specifications',identity+'.json'))
        validation=self.validate_pedagogical_spec(spec)
        if not validation.valid or validation.semantic_sha256!=identity:reject('SPEC_CHANGED','Stored specification is invalid.')
        return spec

    def qualify(self, learning_spec):
        spec = GovernedLearningSpecification.model_validate(learning_spec)
        eligibility = self.evaluate_pedagogical_spec_eligibility(spec)
        if not eligibility.binding_valid: reject('LEARNING_SPEC_INVALID', 'Cannot persist unbound learning evidence.')
        return Qualification(source_learning_spec=spec, eligibility=eligibility,
            lesson_authoring_eligibility=authoring_without_spec(eligibility), governance_state=Governance())

    def validate_qualification(self, qualification):
        try: return validate_qualification_bound(qualification, self.learning)
        except (core.IngestionError, FileNotFoundError, KeyError): return report(qualification, ['SOURCE_OR_POLICY_EVIDENCE_CHANGED'])

    def persist_qualification(self, supplied):
        q = Qualification.model_validate(supplied)
        check = self.validate_qualification(q)
        if not check.valid: reject('QUALIFICATION_INVALID', 'Qualification does not reproduce from source evidence.')
        identity = check.semantic_sha256
        with self.lock:
            if self.storage.safe(identity, 'receipt.json').exists():
                self.read_qualification(identity)
                return json.loads(self.storage.read(identity, 'receipt.json'))
            values = {'qualification': q, 'learning-specification': q.source_learning_spec,
                'eligibility': q.eligibility, 'role-contract': q.eligibility.role_contract,
                'lesson-authoring-eligibility': q.lesson_authoring_eligibility, 'validation': check}
            hashes = {name: self.storage.write((identity, name + '.json'), serial(value)) for name, value in values.items()}
            receipt = dict(qualification_id=identity, semantic_sha256=identity,
                learning_spec_hash=q.eligibility.learning_spec_hash, created_at=now(), artifacts=hashes)
            self.storage.write((identity, 'receipt.json'), serial(receipt))
            return receipt

    def read_qualification(self, identity):
        if not re.fullmatch('[a-f0-9]{64}', identity): reject('NOT_FOUND', 'Unknown qualification.')
        try:
            receipt = json.loads(self.storage.read(identity, 'receipt.json'))
            names = {'qualification', 'learning-specification', 'eligibility', 'role-contract', 'lesson-authoring-eligibility', 'validation'}
            if set(receipt['artifacts']) != names or receipt['qualification_id'] != identity or receipt['semantic_sha256'] != identity:
                reject('QUALIFICATION_CHANGED', 'Receipt identity differs.')
            raw = {n: self.storage.read(identity, n + '.json') for n in names}
            if receipt['artifacts']['qualification'] != identity or any(core.digest(raw[n]) != receipt['artifacts'][n] for n in names):
                reject('QUALIFICATION_CHANGED', 'Saved evidence hash differs.')
            q = Qualification.model_validate_json(raw['qualification']); check = self.validate_qualification(q)
            expected = {'learning-specification': q.source_learning_spec, 'eligibility': q.eligibility,
                'role-contract': q.eligibility.role_contract, 'lesson-authoring-eligibility': q.lesson_authoring_eligibility, 'validation': check}
            if not check.valid or receipt['learning_spec_hash'] != q.eligibility.learning_spec_hash or any(raw[n] != serial(v) for n, v in expected.items()):
                reject('QUALIFICATION_CHANGED', 'Saved evidence no longer reproduces.')
            return q
        except FileNotFoundError: reject('NOT_FOUND', 'Qualification evidence is unavailable.')
        except (KeyError, ValueError): reject('QUALIFICATION_CHANGED', 'Qualification evidence is malformed.')

    def read_pedagogical_spec(self, identity):
        self.read_qualification(identity)
        reject('NOT_CONSTRUCTED', 'This qualification has no constructible pedagogical specification; inspect its missing requirements.')
