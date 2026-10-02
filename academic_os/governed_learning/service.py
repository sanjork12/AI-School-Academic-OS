"""Governed evidence construction and immutable replay, with no production publication."""
import re
import threading
from pydantic import ValidationError
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import serial, Storage, now
from academic_os.curriculum_capability.models import AcademicCapabilityPackage
from .models import LearningSpecificationEligibility, GovernedLearningSpecification, SpecValidation, SpecReceipt
from .policy import POLICY_VERSION, POLICY_SHA256, READY, evaluate_verified
from .construction import construct_verified
from .validation import validate_bound_spec


def error(code, message):
    raise core.IngestionError(code, message)


class GovernedLearningService:
    def __init__(self, capability_service, root=None):
        self.capabilities = capability_service
        self.storage = Storage(root or capability_service.ingestion.storage.safe('runs', 'governed-learning'))
        self.lock = threading.RLock()

    def evaluate_learning_spec_eligibility(self, supplied, expected_package_hash=None):
        raw = supplied.model_dump(mode='json') if hasattr(supplied, 'model_dump') else supplied
        package_hash = core.digest(serial(raw))
        try:
            package = AcademicCapabilityPackage.model_validate(raw)
            package_hash = core.digest(serial(package))
            if expected_package_hash is not None and expected_package_hash != package_hash:
                error('SOURCE_PACKAGE_HASH_MISMATCH', 'Capability package hash differs.')
            self.capabilities.validate_capability_package(package)
            return evaluate_verified(package)
        except (core.IngestionError, ValidationError, FileNotFoundError, KeyError) as exc:
            code = exc.code if isinstance(exc, core.IngestionError) else 'PACKAGE_EVIDENCE_INVALID'
            return LearningSpecificationEligibility(policy_version=POLICY_VERSION, policy_sha256=POLICY_SHA256,
                source_package_hash=package_hash, selected_target_id=None, binding_valid=False,
                status='UNSUPPORTED' if code == 'UNSUPPORTED_CURRICULUM_PROFILE' else 'BLOCKED',
                reason_codes=[code], missing_requirements=['VALID_CURRENT_CAPABILITY_PACKAGE'], warnings=[],
                evidence_refs={}, selected_source_ids=[], objective_results=[], independently_ready_source_ids=[],
                unresolved_source_ids=[], excluded_source_ids=[])

    def build_learning_spec(self, supplied, eligibility_result):
        package = AcademicCapabilityPackage.model_validate(supplied)
        expected = self.evaluate_learning_spec_eligibility(package)
        eligibility = LearningSpecificationEligibility.model_validate(eligibility_result)
        if eligibility != expected:
            error('STALE_ELIGIBILITY', 'Eligibility must match current package evidence and policy exactly.')
        if expected.status not in READY:
            error('LEARNING_SPEC_NOT_ELIGIBLE', 'Every selected objective must qualify; select a smaller scope explicitly if needed.')
        spec = construct_verified(package, eligibility)
        validation = validate_bound_spec(spec, package, expected)
        if not validation.valid:
            error('LEARNING_SPEC_VALIDATION_FAILED', 'Constructed specification failed independent validation.')
        return spec

    def validate_learning_spec(self, supplied):
        raw = supplied.model_dump(mode='json') if hasattr(supplied, 'model_dump') else supplied
        semantic_hash = core.digest(serial(raw))
        try:
            spec = GovernedLearningSpecification.model_validate(raw)
            package = self.capabilities.build_capability_package(spec.curriculum_scope)
            eligibility = self.evaluate_learning_spec_eligibility(package)
            return validate_bound_spec(spec, package, eligibility)
        except (core.IngestionError, ValidationError, FileNotFoundError, KeyError):
            return SpecValidation(valid=False, status='FAIL', errors=['SPEC_OR_SOURCE_EVIDENCE_INVALID'],
                semantic_sha256=semantic_hash, source_package_hash=raw.get('source_package_hash', '') if isinstance(raw, dict) else '',
                policy_version=POLICY_VERSION)

    def persist(self, supplied):
        spec = GovernedLearningSpecification.model_validate(supplied)
        validation = self.validate_learning_spec(spec)
        if not validation.valid:
            error('LEARNING_SPEC_VALIDATION_FAILED', 'Cannot persist invalid specification.')
        package = self.capabilities.build_capability_package(spec.curriculum_scope)
        eligibility = self.evaluate_learning_spec_eligibility(package)
        identity = validation.semantic_sha256
        with self.lock:
            if self.storage.safe(identity, 'receipt.json').exists():
                self.read_learning_spec(identity)
                return SpecReceipt.model_validate_json(self.storage.read(identity, 'receipt.json'))
            artifacts = {}
            for name, value in [('construction-input', package), ('eligibility', eligibility),
                                ('learning-specification', spec), ('validation', validation)]:
                artifacts[name] = self.storage.write((identity, name + '.json'), serial(value))
            receipt = SpecReceipt(spec_id=identity, semantic_sha256=identity,
                source_package_hash=spec.source_package_hash, selected_target_id=spec.curriculum_scope.target_id,
                created_at=now(), artifacts=artifacts)
            self.storage.write((identity, 'receipt.json'), serial(receipt))
            return receipt

    def read_learning_spec(self, identity):
        if not re.fullmatch('[a-f0-9]{64}', identity):
            error('NOT_FOUND', 'Unknown learning specification.')
        try:
            receipt = SpecReceipt.model_validate_json(self.storage.read(identity, 'receipt.json'))
            names = ('construction-input', 'eligibility', 'learning-specification', 'validation')
            if set(receipt.artifacts) != set(names):
                error('SPEC_EVIDENCE_CHANGED', 'Receipt inventory differs.')
            raw = {name: self.storage.read(identity, name + '.json') for name in names}
            if (receipt.spec_id != identity or receipt.semantic_sha256 != identity
                    or receipt.artifacts['learning-specification'] != identity
                    or any(core.digest(raw[name]) != receipt.artifacts[name] for name in names)):
                error('SPEC_EVIDENCE_CHANGED', 'Stored learning evidence changed.')
            package = AcademicCapabilityPackage.model_validate_json(raw['construction-input'])
            spec = GovernedLearningSpecification.model_validate_json(raw['learning-specification'])
            eligibility = LearningSpecificationEligibility.model_validate_json(raw['eligibility'])
            validation = SpecValidation.model_validate_json(raw['validation'])
            current = self.evaluate_learning_spec_eligibility(package, receipt.source_package_hash)
            if (current != eligibility or current.status not in READY
                    or receipt.selected_target_id != spec.curriculum_scope.target_id
                    or core.digest(serial(package)) != spec.source_package_hash
                    or self.validate_learning_spec(spec) != validation or not validation.valid):
                error('SPEC_EVIDENCE_CHANGED', 'Stored evidence no longer reproduces.')
            return spec
        except FileNotFoundError:
            error('NOT_FOUND', 'Learning specification evidence is unavailable.')
        except ValidationError:
            error('SPEC_EVIDENCE_CHANGED', 'Stored evidence has an invalid schema.')
