"""Role-aware offline qualification. No model adapter, transport or live mode."""
from pathlib import Path
from ..ai_authoring.brief import digest
from ..ai_authoring.role_authoring import validate_candidate, compose
from .storage import read, write_new


def evaluate(candidate, inputs, *, support, controlled_case=None, controlled_case_sha256=None):
    options = dict(support=support, controlled_case=controlled_case,
                   controlled_case_sha256=controlled_case_sha256)
    validation = validate_candidate(candidate, inputs, **options)
    composition = compose(candidate, inputs, **options) if validation['accepted'] else None
    data = candidate.model_dump(mode='json') if hasattr(candidate, 'model_dump') else candidate
    hint = support.model_dump(mode='json') if hasattr(support, 'model_dump') else support
    case = controlled_case.model_dump(mode='json') if hasattr(controlled_case, 'model_dump') else controlled_case
    return dict(schema_version='numerical-role-offline-qualification/1', experiment_type='offline_synthetic',
        candidate=data, candidate_sha256=digest(data), support=hint, support_sha256=digest(hint),
        controlled_case=case, controlled_case_sha256=controlled_case_sha256,
        validation=validation, composition=composition, validation_sha256=digest(validation),
        composition_sha256=digest(composition), model_api_calls=0, provider_invocations=0,
        academic_approval=False, ready_for_rendering=False, publishable=False)


def save(record, directory):
    path = Path(directory) / ('role-qualification-'+digest(record)+'.json')
    write_new(path, record, identical_ok=True)
    return path


def rebuild(path, inputs):
    """Recheck immutable evidence with caller-supplied current trusted inputs."""
    path = Path(path)
    record = read(path)
    if path.name != 'role-qualification-'+digest(record)+'.json':
        raise ValueError('Role qualification digest mismatch')
    expected = evaluate(record['candidate'], inputs, support=record['support'],
        controlled_case=record['controlled_case'], controlled_case_sha256=record['controlled_case_sha256'])
    if expected != record: raise ValueError('Role qualification replay differs')
    return expected
