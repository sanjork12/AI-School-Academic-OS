"""Engineering byte/row comparison only; never supplies academic approval."""
import hashlib
import json
from pathlib import Path
import sqlite3
from .storage import file_hash, read
from .reference_baseline import load_active, verify_reference


def capture(database, root):
    root = Path(root).resolve()
    # This is the engineering freeze inventory, not input to any candidate gate.
    manifest, _ = load_active(root)
    inventory = manifest['files']
    conformance = verify_reference(root, database=database)
    files = {}
    matches = conformance['valid']
    for name, expected in inventory.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root): raise ValueError('Baseline path outside project')
        actual = file_hash(path) if path.is_file() else None
        files[name] = actual
        matches = matches and actual == expected
    for directory in (root/'academic_os'/'ai_authoring', root/'academic_os'/'ai_qualification', root/'output'/'p6a_ai_authoring'):
        for path in sorted(directory.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                files[str(path.relative_to(root))] = file_hash(path)
    database = Path(database).resolve()
    tables = {}
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        for table in ('reviews','review_heads','requests','snapshots','snapshot_members','snapshot_blocks','versions','heads'):
            rows = db.execute('SELECT * FROM '+table).fetchall()
            data = json.dumps(sorted(rows, key=repr), ensure_ascii=False, sort_keys=True, default=str).encode()
            tables[table] = {'count': len(rows), 'sha256': hashlib.sha256(data).hexdigest()}
    return {'files': files, 'freeze_inventory_matches': matches,
            'engineering_baseline': conformance,
            'database_sha256': file_hash(database), 'database_tables': tables}
