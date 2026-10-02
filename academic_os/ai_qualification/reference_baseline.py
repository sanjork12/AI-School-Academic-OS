"""Explicit engineering conformance only; never an academic trust authority."""
import hashlib
import json
from pathlib import Path

ACTIVE_REFERENCE_BASELINE = 'v1.16'
ACTIVE_DESCRIPTOR = 'output/reference_freeze_active.json'
ACTIVE_MANIFEST = 'output/reference_freeze_v1_16/reference_manifest.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Baseline path outside project')
    return path


def production_files(root):
    files = set()
    for folder in ('academic_os', 'console_api', 'frontend/src', 'frontend/scripts'):
        files.update(p.relative_to(root).as_posix() for p in (root/folder).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts
            and p.suffix in ('.py','.mjs','.sql','.ts','.tsx','.css','.json','.svg'))
    files.update(p.relative_to(root).as_posix() for p in (root/'frontend').glob('*')
        if p.is_file() and p.suffix in ('.json','.ts','.mjs') and p.name!='next-env.d.ts')
    return sorted(files)


def load_active(root):
    root = Path(root).resolve()
    descriptor = json.loads(local(root, ACTIVE_DESCRIPTOR).read_text(encoding='utf-8'))
    if (descriptor['active_reference_version'] != ACTIVE_REFERENCE_BASELINE
            or descriptor['manifest_path'] != ACTIVE_MANIFEST):
        raise ValueError('Unexpected active engineering baseline')
    path = local(root, ACTIVE_MANIFEST)
    if sha(path) != descriptor['manifest_sha256']:
        raise ValueError('Active reference manifest digest mismatch')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if (manifest['reference_version'] != ACTIVE_REFERENCE_BASELINE
            or manifest['parent_reference'] != 'v1.15'
            or manifest['revision_type'] != 'deterministic_scope_framing'
            or manifest['status'] != 'frozen_baseline_revision'
            or manifest['trust_authority'] is not False):
        raise ValueError('Unexpected engineering manifest identity')
    return manifest, descriptor


def compare_files(root, expected):
    errors = []
    for name, digest in expected.items():
        path = local(root, name)
        if not path.is_file() or sha(path) != digest:
            errors.append('File differs: ' + name)
    return errors


def verify_reference(root, version=ACTIVE_REFERENCE_BASELINE, database=None):
    """v1 through v1.15 check historical artifacts; v1.16 checks current code.

    Historical source bytes are not reconstructed or claimed to be checked.
    Their original recorded hashes remain in the unchanged parent documents.
    """
    if version not in ('v1', 'v1.1', 'v1.2', 'v1.3', 'v1.4', 'v1.5', 'v1.6', 'v1.7', 'v1.8', 'v1.9', 'v1.10', 'v1.11', 'v1.12', 'v1.13', 'v1.14', 'v1.15', 'v1.16'):
        raise ValueError('Unsupported reference version')
    root = Path(root).resolve()
    manifest, descriptor = load_active(root)
    errors = compare_files(root, manifest['lineage']['parent_artifacts'])
    for historical in manifest['historical_baselines'].values():
        errors += compare_files(root, historical)
    if version != ACTIVE_REFERENCE_BASELINE:
        errors += compare_files(root, manifest['historical_reference_artifacts'])
    else:
        errors += compare_files(root, manifest['files'])
        if production_files(root) != manifest['production_inventory']:
            errors.append('Production inventory changed (added or removed file)')
        db = Path(database).resolve() if database is not None else local(root, 'var/p0_q2.sqlite3')
        if not db.is_file() or sha(db) != manifest['database_baseline']['sha256']:
            errors.append('Trusted database differs from approved engineering baseline')
    return dict(reference_version=version, valid=not errors, errors=errors,
                manifest_sha256=descriptor['manifest_sha256'], trust_authority=False,
                verification_scope='current_conformance' if version == ACTIVE_REFERENCE_BASELINE else 'historical_artifact_integrity')
