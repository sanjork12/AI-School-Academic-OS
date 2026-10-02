"""Read-only adapter to the existing trusted service, not an export loader.

Service.snapshot may record a withdrawal. Run it on one consistent, ephemeral
SQLite backup so even a failed product read writes nothing to the real database.
The original source files are still checked by the unchanged service.
"""
from pathlib import Path
import re
import sqlite3
from .storage import Store
from .service import Service


class UnusableSnapshot(ValueError):pass


class _ReadImage(Store):
    def __init__(self,path):
        self.path=Path(path).resolve(strict=True)
        self._savepoint_sequence=0
        self.db=sqlite3.connect(':memory:',isolation_level=None)
        self.db.row_factory=sqlite3.Row
        try:
            source=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
            try:source.backup(self.db)
            finally:source.close()
            version=self.db.execute('SELECT max(version) FROM schema_migrations').fetchone()[0]
            if version!=1:raise ValueError('Unsupported trusted database schema; product reads do not migrate')
        except BaseException:
            self.db.close();raise


def read_usable_snapshots(database,snapshot_ids):
    if isinstance(snapshot_ids,(str,bytes)) or not isinstance(snapshot_ids,(list,tuple)) or not snapshot_ids:
        raise ValueError('Supply a nonempty list of snapshot IDs, not exported content')
    if any(not isinstance(s,str) or not re.fullmatch('[a-f0-9]{64}',s) for s in snapshot_ids):
        raise ValueError('Invalid snapshot ID; detached exports are not accepted')
    store=_ReadImage(database)
    try:
        service=Service(store);result={}
        for sid in sorted(set(snapshot_ids)):
            status=service.snapshot(sid)
            if not status['usable']:
                raise UnusableSnapshot('Snapshot unusable: '+sid+'; '+ '; '.join(b['reason'] for b in status['blocks']))
            result[sid]=status['payload']
        return result
    finally:store.close()
