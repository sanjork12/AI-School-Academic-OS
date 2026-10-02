CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY);
INSERT INTO schema_migrations VALUES(1);
CREATE TABLE versions(object_key TEXT NOT NULL, version TEXT NOT NULL, content TEXT NOT NULL,
 created_at TEXT NOT NULL, PRIMARY KEY(object_key,version));
CREATE TABLE heads(object_key TEXT PRIMARY KEY, version TEXT NOT NULL,
 FOREIGN KEY(object_key,version) REFERENCES versions(object_key,version));
CREATE TABLE requests(request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE reviews(decision_id TEXT PRIMARY KEY, object_key TEXT NOT NULL, object_version TEXT NOT NULL,
 reviewer TEXT NOT NULL, created_at TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL,
 dependency_digest TEXT NOT NULL, dependency_manifest TEXT NOT NULL, supersedes TEXT REFERENCES reviews(decision_id),
 FOREIGN KEY(object_key,object_version) REFERENCES versions(object_key,version));
CREATE TABLE review_heads(object_key TEXT PRIMARY KEY, decision_id TEXT NOT NULL REFERENCES reviews(decision_id));
CREATE TABLE snapshots(snapshot_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE snapshot_members(snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), object_key TEXT NOT NULL,
 version TEXT NOT NULL, PRIMARY KEY(snapshot_id,object_key));
CREATE TABLE snapshot_blocks(snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), event TEXT NOT NULL,
 reason TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(snapshot_id,event));
