"""Read current bound evidence, build a pure package, then persist content-addressed bytes.

Historical JSON approval labels are not trusted snapshot receipts. No database writer,
provider client, parser invocation or Standard Deviation routing is used here.
"""
import json
import re
import threading
from pathlib import Path
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.models import SelectedCurriculumTarget, Warning
from academic_os.curriculum_ingestion.service import Storage, serial, now
from academic_os.curriculum_ingestion.validation import validate_curriculum
from .models import AcademicCapabilityPackage, CanonicalBinding, ObjectiveEvidence, Coverage, Eligibility, PackageReceipt

PROMOTED = 'output/topic2_canonical_promoted.json'
DECISIONS = 'output/topic2_human_review_decisions.json'
PROPOSALS = 'output/topic2_ai_mapping_proposals.json'
MANIFEST = Path(__file__).with_name('evidence_manifest.json')


def reject(code, message):
    raise core.IngestionError(code, message)


def read_historical_evidence():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    values = {}
    for name, expected in manifest['files'].items():
        raw = (core.ROOT / name).read_bytes()
        if core.digest(raw) != expected:
            reject('EVIDENCE_CHANGED', 'Historical mapping evidence differs from its recorded digest.')
        values[name] = json.loads(raw)
    return values, manifest['files']


def canonical_for(objective, tier, subtopic, values, hashes):
    """Exact source wording + tier + ID binds historical association, never trust."""
    historical = values[f'output/topic2_{tier}_parsed.json']
    matches = [o for s in historical['subtopics'] if s['code'] == subtopic
               for o in s['objectives'] if o['source_id'] == objective.source_id]
    if len(matches) != 1 or matches[0]['code'] != objective.objective_code or matches[0]['official_text'] != objective.official_text:
        return 'REVIEW_REQUIRED', [], []
    promoted = values[PROMOTED]
    canonical = {c['canonical_id']: c for c in promoted['canonical_objectives']}
    bindings = []
    for mapping in promoted['mappings']:
        if mapping['official_source_id'] != objective.source_id:
            continue
        cid = mapping['canonical_id']
        if cid not in canonical:
            reject('MAPPING_BINDING_INVALID', 'Historical canonical definition is missing.')
        decisions = [d['decision_id'] for d in values[DECISIONS]['decisions']
                     if d['decision'] == 'approve' and d.get('reviewed_by') == 'human'
                     and mapping in d.get('approved_official_mappings', [])]
        bindings.append(CanonicalBinding(official_source_id=objective.source_id, canonical_id=cid,
            canonical_wording=canonical[cid]['description'], relationship=mapping['relationship'],
            evidence_path=PROMOTED, evidence_sha256=hashes[PROMOTED],
            historical_review_status=mapping['review_status'], mapping_method=mapping['mapping_method'],
            human_review_evidence='RECORDED_DECISION' if decisions else 'NOT_AVAILABLE',
            decision_ids=sorted(decisions), historically_promoted=True))
    proposals = sorted(p['proposed_canonical_id'] for p in values[PROPOSALS]['proposals']
                       if p['official_source_id'] == objective.source_id)
    return ('MAPPED' if bindings else 'REVIEW_REQUIRED' if proposals else 'UNMAPPED'), bindings, proposals


class AcademicCapabilityService:
    def __init__(self, ingestion, root=None):
        self.ingestion = ingestion
        self.storage = Storage(root or ingestion.storage.safe('runs', 'capability-packages'))
        self.lock = threading.RLock()

    def _resolve(self, supplied):
        try:
            return self._resolve_bound(supplied)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            if isinstance(exc, core.IngestionError):
                raise
            reject('EVIDENCE_UNAVAILABLE', 'Required source, parse or validation evidence is missing or malformed.')

    def _resolve_bound(self, supplied):
        target = SelectedCurriculumTarget.model_validate(supplied)
        if target.profile != core.PROFILE or target.tier not in ('Foundation', 'Higher'):
            reject('UNSUPPORTED_CURRICULUM_PROFILE', 'Only a single Foundation or Higher 4MA1 Topic 2 selection is supported.')
        run = self.ingestion.get(target.run_id)
        tree = self.ingestion.tree(target.run_id)
        parsed = self.ingestion.output(target.run_id, 'parsed')
        validation = self.ingestion.output(target.run_id, 'validation')
        # A valid JSON hash alone does not prove it is the matching validation/tree.
        expected_validation = validate_curriculum(parsed, run.tier)
        if validation != expected_validation or not validation['structure_valid'] or not validation['source_ids_valid']:
            reject('VALIDATION_BINDING_INVALID', 'Validation must reproduce from this parsed curriculum.')
        rebuilt_tree = self.ingestion.build_tree(run, parsed, tree.validation)
        if tree != rebuilt_tree or tree.tier != run.tier.title() or tree.profile != core.PROFILE or tree.source_sha256 != core.KNOWN_SHA:
            reject('SOURCE_BINDING_INVALID', 'Run, tree and source identities disagree.')
        exrun = self.ingestion.get(run.extraction_run_id)
        extraction = self.ingestion.output(exrun.run_id, 'extraction')
        if (exrun.status != 'succeeded' or exrun.operation != 'extract' or exrun.document_id != run.document_id
                or exrun.tier != run.tier or exrun.profile != run.profile
                or exrun.source_sha256 != run.source_sha256 or extraction['source_sha256'] != run.source_sha256
                or (run.start_page, run.end_page) != core.RANGES[run.tier]
                or (extraction['start_page'], extraction['end_page']) != core.RANGES[run.tier]):
            reject('SOURCE_BINDING_INVALID', 'Extraction is not bound to this tier/document.')
        # Infer only the existing API's topic/subtopic/single-objective selection shapes.
        all_target = self.ingestion.capabilities(run.run_id, target.subtopic_code).target
        if target.objective_codes == all_target.objective_codes:
            fresh = all_target
        elif target.subtopic_code and len(target.objective_codes) == 1:
            fresh = self.ingestion.capabilities(run.run_id, target.subtopic_code, target.objective_codes[0]).target
        else:
            reject('STALE_SELECTION', 'Selection is not a supported complete scope or single objective.')
        if target != fresh:
            reject('STALE_SELECTION', 'Refresh selection; its identity or evidence binding differs.')
        return fresh, run, tree, exrun

    def build_capability_package(self, selected_target):
        target, run, tree, exrun = self._resolve(selected_target)
        values, hashes = read_historical_evidence()
        warnings = list(tree.warnings)
        objectives = []
        for topic in tree.topics:
            for sub in topic.subtopics:
                for obj in sub.objectives:
                    if obj.source_id not in target.source_ids:
                        continue
                    status, bindings, proposals = canonical_for(obj, run.tier, sub.subtopic_code, values, hashes)
                    if status != 'MAPPED':
                        warnings.append(Warning(code='CANONICAL_' + status, message=obj.source_id + ': ' + status))
                    objectives.append(ObjectiveEvidence(
                        objective_identity=core.digest(serial([target.document_id, target.run_id, target.tier, obj.source_id])),
                        objective_code=obj.objective_code, official_text=obj.official_text, source_id=obj.source_id,
                        tier=target.tier, topic_code=topic.topic_code, topic_name=topic.topic_name,
                        subtopic_code=sub.subtopic_code, subtopic_name=sub.subtopic_name,
                        subtopic_notes=list(sub.notes),
                        source_sha256=target.source_sha256, warnings=list(tree.warnings),
                        validation_sha256=target.validation_sha256, mapping_status=status,
                        canonical_bindings=bindings, ai_proposal_ids=proposals))
        if [o.source_id for o in objectives] != target.source_ids:
            reject('SOURCE_BINDING_INVALID', 'Selected objectives must exactly match the source sequence.')
        warnings.append(Warning(code='HUMAN_REVIEW_REQUIRED', message='Uploaded source and mappings have no target-specific approval or trusted snapshot binding.'))
        missing = ['TARGET_SOURCE_VERIFICATION', 'TARGET_GOVERNED_CANONICAL_BINDINGS',
                   'APPROVED_CONCEPT_CAPABILITY_TASK_RELATIONS', 'REVIEWED_ASSESSMENT_EVIDENCE',
                   'CURRENT_USABLE_TRUSTED_SNAPSHOTS', 'TOPIC_CATALOG_ADAPTER',
                   'CONSISTENT_TEACHER_TOPIC_2_AND_ASSESSMENT_INTELLIGENCE_1']
        if any(o.mapping_status != 'MAPPED' for o in objectives):
            missing.append('RESOLVED_CANONICAL_SCOPE_OR_EXPLICIT_GOVERNED_PARTIAL_SCOPE')
        eligibility = {'CURRICULUM_BROWSABLE': Eligibility(eligible=True, status='PASS_WITH_WARNINGS',
                        reason_code='VALIDATED_SOURCE_BOUND_CURRICULUM', missing_requirements=[])}
        downstream = {
            'LEARNING_SPEC_ELIGIBLE': missing,
            'PEDAGOGY_ELIGIBLE': ['ELIGIBLE_LEARNING_SPECIFICATION', 'BOUNDED_PEDAGOGY_ADAPTER'],
            'LESSON_AUTHORING_ELIGIBLE': ['ELIGIBLE_PEDAGOGICAL_SPECIFICATION', 'BOUNDED_AUTHORING_ADAPTER'],
            'QUESTION_AUTHORING_ELIGIBLE': ['ELIGIBLE_LEARNING_SPECIFICATION', 'REVIEWED_QUESTION_SCOPE_AND_POLICY'],
            'PRESENTATION_ELIGIBLE': ['VALIDATED_AUTHORED_CONTENT', 'RENDERER_READY_PROFILE']}
        for name, requirements in downstream.items():
            eligibility[name] = Eligibility(eligible=False, status='BLOCKED',
                reason_code='ACADEMIC_EVIDENCE_OR_ADAPTER_MISSING', missing_requirements=requirements)
        coverage = Coverage(selected_objectives=len(objectives),
            canonical_mapped=sum(o.mapping_status == 'MAPPED' for o in objectives),
            unmapped=sum(o.mapping_status == 'UNMAPPED' for o in objectives),
            review_required=sum(o.mapping_status == 'REVIEW_REQUIRED' for o in objectives), warnings=len(warnings))
        return AcademicCapabilityPackage(target=target,
            source_binding=dict(document_id=target.document_id, source_sha256=target.source_sha256,
                parser_run_id=run.run_id, parser_run_sha256=target.run_sha256, parsed_sha256=target.parsed_sha256,
                validation_sha256=target.validation_sha256, tree_sha256=target.tree_sha256,
                extraction_run_id=exrun.run_id, extraction_sha256=exrun.outputs['extraction'], parser_mode=run.mode),
            objectives=objectives, coverage=coverage, unresolved_items=missing, warnings=warnings,
            eligibility=eligibility, supported_capabilities=['CURRICULUM_BROWSABLE'],
            unsupported_capabilities=list(downstream), evidence=hashes)

    def validate_capability_package(self, package):
        package = AcademicCapabilityPackage.model_validate(package)
        expected = self.build_capability_package(package.target)
        if serial(package) != serial(expected):
            reject('PACKAGE_CHANGED', 'Package does not reproduce from its current bound evidence.')
        return dict(status='PASS_WITH_WARNINGS' if package.warnings else 'PASS',
                    valid=True, package_sha256=core.digest(serial(package)), model_calls=0)

    def persist(self, package):
        checked = self.validate_capability_package(package)
        identity = checked['package_sha256']
        with self.lock:
            if self.storage.safe(identity, 'receipt.json').exists():
                self.read_capability_package(identity)
                return PackageReceipt.model_validate_json(self.storage.read(identity, 'receipt.json'))
            receipt = PackageReceipt(package_id=identity, package_sha256=identity,
                source_target_id=package.target.target_id, construction_version=package.construction_version, created_at=now())
            self.storage.write((identity, 'package.json'), serial(package))
            self.storage.write((identity, 'receipt.json'), serial(receipt))
            return receipt

    def read_capability_package(self, identity):
        if not re.fullmatch('[a-f0-9]{64}', identity):
            reject('NOT_FOUND', 'Unknown capability package.')
        try:
            raw = self.storage.read(identity, 'package.json')
            receipt = PackageReceipt.model_validate_json(self.storage.read(identity, 'receipt.json'))
        except FileNotFoundError:
            reject('NOT_FOUND', 'Unknown capability package.')
        if core.digest(raw) != identity or receipt.package_id != identity or receipt.package_sha256 != identity:
            reject('PACKAGE_CHANGED', 'Stored package digest differs.')
        package = AcademicCapabilityPackage.model_validate_json(raw)
        if receipt.source_target_id != package.target.target_id or receipt.construction_version != package.construction_version:
            reject('PACKAGE_CHANGED', 'Receipt does not match this package.')
        self.validate_capability_package(package)
        return package
