"""SQLite persistence, append-only history and explicit transactions."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3

def now():return datetime.now(timezone.utc).isoformat()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(path),timeout=10,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self._savepoint_sequence=0
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA busy_timeout=10000')
        # One EXCLUSIVE migration transaction, safe across simultaneous initialisation.
        with self.transaction('EXCLUSIVE'):
            if not self.db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone():
                sql=(Path(__file__).parent/'migrations/001_initial.sql').read_text(encoding='utf-8')
                for statement in sql.split(';'):
                    if statement.strip():self.db.execute(statement)
                for table in ['versions','reviews','requests','snapshots','snapshot_members','snapshot_blocks']:
                    for op in ['UPDATE','DELETE']:
                        self.db.execute(f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END")
            if self.db.execute('SELECT max(version) FROM schema_migrations').fetchone()[0]!=1:
                raise ValueError('Unsupported database schema version')
    @contextmanager
    def transaction(self,mode='IMMEDIATE'):
        # A bundle owns the outer transaction; ordinary Service.review calls keep
        # their own rollback boundary without committing the outer decision.
        if self.db.in_transaction:
            self._savepoint_sequence+=1
            name='service_'+str(self._savepoint_sequence)
            self.db.execute('SAVEPOINT '+name)
            try:yield;self.db.execute('RELEASE SAVEPOINT '+name)
            except BaseException:
                self.db.execute('ROLLBACK TO SAVEPOINT '+name)
                self.db.execute('RELEASE SAVEPOINT '+name)
                raise
            return
        self.db.execute('BEGIN '+mode)
        try:yield;self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
    def close(self):self.db.close()
    def graph(self):
        return {r['object_key']:dict(version=r['version'],record=json.loads(r['content'])) for r in self.db.execute('SELECT v.* FROM versions v JOIN heads h USING(object_key,version)')}
    def decisions(self):
        return {r['object_key']:dict(r) for r in self.db.execute('SELECT r.* FROM reviews r JOIN review_heads h USING(object_key,decision_id)')}
    def retry(self,request_id,request_digest):
        if not isinstance(request_id,str) or not request_id.strip():raise ValueError('A nonempty idempotency request ID is required')
        row=self.db.execute('SELECT * FROM requests WHERE request_id=?',(request_id,)).fetchone()
        if row:
            if row['digest']!=request_digest:raise ValueError('Idempotency key conflict: '+request_id)
            return json.loads(row['result'])
    def remember(self,request_id,request_digest,result):
        self.db.execute('INSERT INTO requests VALUES(?,?,?)',(request_id,request_digest,canonical(result)))
    def invalidate(self,keys,event,reason):
        for key in keys:
            self.db.execute('INSERT OR IGNORE INTO snapshot_blocks SELECT snapshot_id,?,?,? FROM snapshot_members WHERE object_key=?',(event,reason,now(),key))
