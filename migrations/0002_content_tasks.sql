-- 内容、身份、制品与编排存储。外部IO、权限和状态竞态仍由应用短事务实现。

CREATE TABLE principals (
id TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('human','worker')),
role TEXT NOT NULL CHECK ((kind='human' AND role IN ('user','maintainer')) OR (kind='worker' AND role='worker')),
created_at TEXT NOT NULL
) STRICT;

CREATE TABLE auth_tokens (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
token_sha256 TEXT NOT NULL CHECK ((length(token_sha256) = 64 AND token_sha256 NOT GLOB '*[^0-9a-f]*')), purpose TEXT NOT NULL CHECK (purpose IN ('cli','worker')), capabilities_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(capabilities_json) AND json_type(capabilities_json) = 'array'),
created_at TEXT NOT NULL, revoked_at TEXT, UNIQUE(token_sha256)
) STRICT;

CREATE TABLE browser_sessions (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
session_sha256 TEXT NOT NULL CHECK ((length(session_sha256) = 64 AND session_sha256 NOT GLOB '*[^0-9a-f]*')), csrf_sha256 TEXT NOT NULL CHECK ((length(csrf_sha256) = 64 AND csrf_sha256 NOT GLOB '*[^0-9a-f]*')), expires_at TEXT NOT NULL, revoked_at TEXT, created_at TEXT NOT NULL,
UNIQUE(session_sha256)
) STRICT;

CREATE TABLE pairing_codes (
principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
code_sha256 TEXT NOT NULL CHECK ((length(code_sha256) = 64 AND code_sha256 NOT GLOB '*[^0-9a-f]*')), expires_at TEXT NOT NULL, consumed_at TEXT,
created_at TEXT NOT NULL, PRIMARY KEY(code_sha256)
) STRICT;

CREATE TABLE artifacts (
id TEXT PRIMARY KEY NOT NULL, sha256 TEXT NOT NULL CHECK ((length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')), size_bytes INTEGER NOT NULL CHECK(size_bytes>=0),
media_type TEXT NOT NULL CHECK(length(media_type)>0), validation_status TEXT NOT NULL CHECK(validation_status IN ('validated','invalid')),
created_at TEXT NOT NULL, UNIQUE(sha256), UNIQUE(id,sha256), UNIQUE(id,sha256,size_bytes)
) STRICT;

CREATE TABLE artifact_owners (
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT, PRIMARY KEY(artifact_id,principal_id)
) STRICT;

CREATE TABLE artifact_dependencies (
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
depends_on_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
PRIMARY KEY(artifact_id,depends_on_id), CHECK(artifact_id!=depends_on_id)
) STRICT;

CREATE TABLE configurations (
sha256 TEXT NOT NULL CHECK ((length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')), config_json TEXT NOT NULL CHECK (json_valid(config_json) AND json_type(config_json) = 'object'), created_at TEXT NOT NULL, PRIMARY KEY(sha256),
CHECK(config_json=fv_canonical_json(config_json)), CHECK(sha256=fv_config_hash(config_json))
) STRICT;

CREATE TABLE books (
id TEXT PRIMARY KEY NOT NULL, title TEXT NOT NULL CHECK(length(title)>0), authors_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(authors_json) AND json_type(authors_json) = 'array'),
revision INTEGER NOT NULL CHECK(revision>0), current_text_revision_id TEXT, created_at TEXT NOT NULL,
FOREIGN KEY(id,current_text_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE source_assets (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, role TEXT NOT NULL CHECK(role IN ('primary','reference')),
format TEXT NOT NULL CHECK(format IN ('epub','pdf_text','pdf_scanned','pdf_mixed')), edition TEXT NOT NULL,
created_at TEXT NOT NULL, UNIQUE(book_id,id)
) STRICT;

CREATE TABLE text_revisions (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
revision INTEGER NOT NULL CHECK(revision>0), parent_revision_id TEXT, structure_artifact_id TEXT NOT NULL, structure_sha256 TEXT NOT NULL CHECK ((length(structure_sha256) = 64 AND structure_sha256 NOT GLOB '*[^0-9a-f]*')),
created_at TEXT NOT NULL, UNIQUE(book_id,revision), UNIQUE(book_id,id),
FOREIGN KEY(book_id,parent_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT,
FOREIGN KEY(structure_artifact_id,structure_sha256) REFERENCES artifacts(id,sha256) ON DELETE RESTRICT,
CHECK(parent_revision_id IS NULL OR parent_revision_id!=id)
) STRICT;

CREATE TABLE source_spans (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL, text_revision_id TEXT NOT NULL, source_asset_id TEXT NOT NULL,
locator TEXT NOT NULL CHECK(length(locator)>0), start_offset INTEGER NOT NULL CHECK(start_offset>=0),
end_offset INTEGER NOT NULL CHECK(end_offset>=start_offset), UNIQUE(text_revision_id,id),
FOREIGN KEY(book_id,text_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT,
FOREIGN KEY(book_id,source_asset_id) REFERENCES source_assets(book_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE content_units (
id TEXT PRIMARY KEY NOT NULL, text_revision_id TEXT NOT NULL REFERENCES text_revisions(id) ON DELETE RESTRICT,
position INTEGER NOT NULL CHECK(position>=0), kind TEXT NOT NULL CHECK(kind IN ('chapter','paragraph','sentence')),
source_span_id TEXT NOT NULL, UNIQUE(text_revision_id,position), UNIQUE(text_revision_id,id),
FOREIGN KEY(text_revision_id,source_span_id) REFERENCES source_spans(text_revision_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE text_mappings (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL, from_revision_id TEXT, to_revision_id TEXT NOT NULL, unit_id TEXT NOT NULL,
source_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
display_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
spoken_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
comparison_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
transform_kind TEXT NOT NULL, start_offset INTEGER NOT NULL CHECK(start_offset>=0),
end_offset INTEGER NOT NULL CHECK(end_offset>=start_offset),
FOREIGN KEY(book_id,from_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT,
FOREIGN KEY(book_id,to_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT,
FOREIGN KEY(to_revision_id,unit_id) REFERENCES content_units(text_revision_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE voices (
id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL CHECK(length(name)>0),
revision INTEGER NOT NULL CHECK(revision>0), created_at TEXT NOT NULL
) STRICT;

CREATE TABLE voice_versions (
id TEXT PRIMARY KEY NOT NULL, voice_id TEXT NOT NULL REFERENCES voices(id) ON DELETE RESTRICT,
version INTEGER NOT NULL CHECK(version>0), reference_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
reference_text TEXT NOT NULL CHECK(length(reference_text)>0), model_revisions_json TEXT NOT NULL CHECK (json_valid(model_revisions_json) AND json_type(model_revisions_json) = 'array'),
config_sha256 TEXT NOT NULL REFERENCES configurations(sha256) ON DELETE RESTRICT,
approved_review_id TEXT REFERENCES review_records(id) ON DELETE RESTRICT,
created_at TEXT NOT NULL, UNIQUE(voice_id,version)
) STRICT;

CREATE TABLE production_revisions (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
text_revision_id TEXT NOT NULL, voice_version_id TEXT NOT NULL REFERENCES voice_versions(id) ON DELETE RESTRICT,
model_revision TEXT NOT NULL CHECK(length(model_revision)>0), config_sha256 TEXT NOT NULL REFERENCES configurations(sha256) ON DELETE RESTRICT,
snapshot_sha256 TEXT NOT NULL CHECK ((length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*')), control_state TEXT NOT NULL DEFAULT 'active' CHECK(control_state IN ('active','pausing','paused','cancelled')),
control_revision INTEGER NOT NULL DEFAULT 1 CHECK(control_revision>0), quality_revision INTEGER NOT NULL DEFAULT 1 CHECK(quality_revision>0), created_at TEXT NOT NULL,
UNIQUE(id,snapshot_sha256), UNIQUE(id,book_id), UNIQUE(id,text_revision_id),
FOREIGN KEY(book_id,text_revision_id) REFERENCES text_revisions(book_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE production_scope (
production_id TEXT NOT NULL, text_revision_id TEXT NOT NULL, unit_id TEXT NOT NULL,
position INTEGER NOT NULL CHECK(position>=0), PRIMARY KEY(production_id,unit_id), UNIQUE(production_id,position),
FOREIGN KEY(production_id,text_revision_id) REFERENCES production_revisions(id,text_revision_id) ON DELETE RESTRICT,
FOREIGN KEY(text_revision_id,unit_id) REFERENCES content_units(text_revision_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE scopes (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT REFERENCES production_revisions(id) ON DELETE RESTRICT,
voice_version_id TEXT REFERENCES voice_versions(id) ON DELETE RESTRICT, snapshot_sha256 TEXT NOT NULL CHECK ((length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*')),
CHECK((production_id IS NOT NULL AND voice_version_id IS NULL) OR (production_id IS NULL AND voice_version_id IS NOT NULL)),
UNIQUE(production_id,id)
) STRICT;

CREATE TABLE scope_units (
scope_id TEXT NOT NULL, production_id TEXT NOT NULL, unit_id TEXT NOT NULL, PRIMARY KEY(scope_id,unit_id),
FOREIGN KEY(production_id,scope_id) REFERENCES scopes(production_id,id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,unit_id) REFERENCES production_scope(production_id,unit_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE workers (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
protocol_version INTEGER NOT NULL CHECK(protocol_version=1), name TEXT NOT NULL, platform TEXT NOT NULL CHECK(platform IN ('container','macos')),
capabilities_json TEXT NOT NULL CHECK (json_valid(capabilities_json) AND json_type(capabilities_json) = 'array'), model_revisions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(model_revisions_json) AND json_type(model_revisions_json) = 'array'), registered_at TEXT NOT NULL, UNIQUE(principal_id)
) STRICT;

CREATE TABLE app_generations (
id TEXT PRIMARY KEY NOT NULL, started_at TEXT NOT NULL, ended_at TEXT
) STRICT;

CREATE TABLE tasks (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL REFERENCES production_revisions(id) ON DELETE RESTRICT,
stage TEXT NOT NULL CHECK(length(stage)>0), unit_key TEXT NOT NULL, input_snapshot_sha256 TEXT NOT NULL CHECK ((length(input_snapshot_sha256) = 64 AND input_snapshot_sha256 NOT GLOB '*[^0-9a-f]*')),
state TEXT NOT NULL CHECK(state IN ('queued','running','pause_requested','paused','completed','failed','cancelled')),
revision INTEGER NOT NULL CHECK(revision>0), created_at TEXT NOT NULL,
UNIQUE(production_id,stage,unit_key,input_snapshot_sha256), UNIQUE(id,production_id), UNIQUE(id,input_snapshot_sha256)
) STRICT;

CREATE TABLE task_dependencies (
task_id TEXT NOT NULL, depends_on_id TEXT NOT NULL, production_id TEXT NOT NULL,
PRIMARY KEY(task_id,depends_on_id), CHECK(task_id!=depends_on_id),
FOREIGN KEY(task_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(depends_on_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE attempts (
task_id TEXT NOT NULL, attempt_no INTEGER NOT NULL CHECK(attempt_no>0),
worker_id TEXT NOT NULL REFERENCES workers(id) ON DELETE RESTRICT, app_generation TEXT NOT NULL REFERENCES app_generations(id) ON DELETE RESTRICT,
input_snapshot_sha256 TEXT NOT NULL CHECK ((length(input_snapshot_sha256) = 64 AND input_snapshot_sha256 NOT GLOB '*[^0-9a-f]*')), state TEXT NOT NULL CHECK(state IN ('running','completed','failed','expired','cancelled')),
created_at TEXT NOT NULL, PRIMARY KEY(task_id,attempt_no),
FOREIGN KEY(task_id,input_snapshot_sha256) REFERENCES tasks(id,input_snapshot_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE leases (
id TEXT PRIMARY KEY NOT NULL, task_id TEXT NOT NULL, attempt_no INTEGER NOT NULL,
token_sha256 TEXT NOT NULL CHECK ((length(token_sha256) = 64 AND token_sha256 NOT GLOB '*[^0-9a-f]*')), expires_at TEXT NOT NULL, revoked_at TEXT, created_at TEXT NOT NULL,
UNIQUE(task_id,attempt_no), UNIQUE(token_sha256),
FOREIGN KEY(task_id,attempt_no) REFERENCES attempts(task_id,attempt_no) ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX one_current_lease ON leases(task_id) WHERE revoked_at IS NULL;

CREATE TRIGGER lease_no_reactivation BEFORE UPDATE ON leases WHEN OLD.revoked_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, '旧租约不得恢复授权'); END;

CREATE TABLE task_inputs (
task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, PRIMARY KEY(task_id,artifact_id)
) STRICT;

CREATE TABLE task_outputs (
task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, PRIMARY KEY(task_id,artifact_id)
) STRICT;

CREATE TABLE result_receipts (
id TEXT PRIMARY KEY NOT NULL, task_id TEXT NOT NULL UNIQUE, attempt_no INTEGER NOT NULL,
principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT, request_id TEXT NOT NULL,
payload_sha256 TEXT NOT NULL CHECK ((length(payload_sha256) = 64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*')), result_summary TEXT NOT NULL, accepted_at TEXT NOT NULL,
FOREIGN KEY(task_id,attempt_no) REFERENCES attempts(task_id,attempt_no) ON DELETE RESTRICT
) STRICT;

CREATE TABLE idempotency_receipts (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
operation TEXT NOT NULL, request_id TEXT NOT NULL, payload_sha256 TEXT NOT NULL CHECK ((length(payload_sha256) = 64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*')),
response_status INTEGER NOT NULL CHECK(response_status BETWEEN 200 AND 599), response_json TEXT CHECK(response_json IS NULL OR (json_valid(response_json) AND json_type(response_json)='object')),
created_at TEXT NOT NULL, UNIQUE(principal_id,operation,request_id), CHECK(response_status!=204 OR response_json IS NULL)
) STRICT;

CREATE TABLE checkpoints (
id TEXT PRIMARY KEY NOT NULL, task_id TEXT NOT NULL, attempt_no INTEGER NOT NULL, production_id TEXT NOT NULL,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, input_snapshot_sha256 TEXT NOT NULL CHECK ((length(input_snapshot_sha256) = 64 AND input_snapshot_sha256 NOT GLOB '*[^0-9a-f]*')), adapter_version TEXT NOT NULL,
created_at TEXT NOT NULL, UNIQUE(id,task_id), UNIQUE(id,production_id), FOREIGN KEY(task_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT, FOREIGN KEY(task_id,attempt_no) REFERENCES attempts(task_id,attempt_no) ON DELETE RESTRICT,
FOREIGN KEY(task_id,input_snapshot_sha256) REFERENCES tasks(id,input_snapshot_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE checkpoint_units (
checkpoint_id TEXT NOT NULL, production_id TEXT NOT NULL,
unit_id TEXT NOT NULL, artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
PRIMARY KEY(checkpoint_id,unit_id,artifact_id),
FOREIGN KEY(checkpoint_id,production_id) REFERENCES checkpoints(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,unit_id) REFERENCES production_scope(production_id,unit_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE synthesis_blocks (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL REFERENCES production_revisions(id) ON DELETE RESTRICT,
position INTEGER NOT NULL CHECK(position>=0), input_sha256 TEXT NOT NULL CHECK ((length(input_sha256) = 64 AND input_sha256 NOT GLOB '*[^0-9a-f]*')), rules_version TEXT NOT NULL,
UNIQUE(production_id,position), UNIQUE(id,production_id)
) STRICT;

CREATE TABLE sentence_links (
block_id TEXT NOT NULL, production_id TEXT NOT NULL, sentence_id TEXT NOT NULL,
sequence INTEGER NOT NULL CHECK(sequence>=0), start_offset INTEGER NOT NULL CHECK(start_offset>=0), end_offset INTEGER NOT NULL CHECK(end_offset>start_offset),
PRIMARY KEY(block_id,sequence), FOREIGN KEY(block_id,production_id) REFERENCES synthesis_blocks(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,sentence_id) REFERENCES production_scope(production_id,unit_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE review_records (
id TEXT PRIMARY KEY NOT NULL, artifact_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL CHECK ((length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*')),
scope_id TEXT NOT NULL REFERENCES scopes(id) ON DELETE RESTRICT, dimension TEXT NOT NULL,
conclusion TEXT NOT NULL CHECK(conclusion IN ('approved','rejected','uncertain')),
voice_version_id TEXT REFERENCES voice_versions(id) ON DELETE RESTRICT, actor_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
comment TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(artifact_id,artifact_sha256) REFERENCES artifacts(id,sha256) ON DELETE RESTRICT
) STRICT;

CREATE TRIGGER review_requires_human BEFORE INSERT ON review_records
BEGIN SELECT RAISE(ABORT, '人工记录不能由执行器创建') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.actor_id AND kind='human'); END;

CREATE TRIGGER voice_approval_matches BEFORE UPDATE OF approved_review_id ON voice_versions
WHEN NEW.approved_review_id IS NOT NULL
BEGIN SELECT RAISE(ABORT, '声音认可必须匹配用户试听记录') WHERE NOT EXISTS (
SELECT 1 FROM review_records WHERE id=NEW.approved_review_id AND voice_version_id=NEW.id AND conclusion='approved'); END;

CREATE TABLE uploads (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
task_id TEXT REFERENCES tasks(id) ON DELETE RESTRICT, size_bytes INTEGER NOT NULL CHECK(size_bytes>=0), sha256 TEXT NOT NULL CHECK ((length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')),
chunk_size_bytes INTEGER NOT NULL CHECK(chunk_size_bytes>0), media_type TEXT NOT NULL, purpose TEXT NOT NULL,
state TEXT NOT NULL CHECK(state IN ('open','completed','expired')), artifact_id TEXT, expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
CHECK((state='completed' AND artifact_id IS NOT NULL) OR (state!='completed' AND artifact_id IS NULL)),
FOREIGN KEY(artifact_id,sha256,size_bytes) REFERENCES artifacts(id,sha256,size_bytes) ON DELETE RESTRICT
) STRICT;

CREATE TABLE upload_chunks (
upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE RESTRICT, chunk_index INTEGER NOT NULL CHECK(chunk_index>=0),
size_bytes INTEGER NOT NULL CHECK(size_bytes>0), sha256 TEXT NOT NULL CHECK ((length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')), PRIMARY KEY(upload_id,chunk_index)
) STRICT;

CREATE TABLE audit_events (
server_sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT, operation TEXT NOT NULL,
target_kind TEXT NOT NULL, target_id TEXT NOT NULL, revision INTEGER CHECK(revision>0), summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(summary_json) AND json_type(summary_json) = 'object'), created_at TEXT NOT NULL
) STRICT;

CREATE TABLE dependency_nodes (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL REFERENCES production_revisions(id) ON DELETE RESTRICT,
kind TEXT NOT NULL CHECK(kind IN ('task','artifact')), task_id TEXT, artifact_id TEXT REFERENCES artifacts(id) ON DELETE RESTRICT,
CHECK((kind='task' AND task_id IS NOT NULL AND artifact_id IS NULL) OR (kind='artifact' AND task_id IS NULL AND artifact_id IS NOT NULL)),
UNIQUE(production_id,id), FOREIGN KEY(task_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE dependency_edges (
production_id TEXT NOT NULL, node_id TEXT NOT NULL, depends_on_id TEXT NOT NULL,
PRIMARY KEY(node_id,depends_on_id), CHECK(node_id!=depends_on_id),
FOREIGN KEY(production_id,node_id) REFERENCES dependency_nodes(production_id,id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,depends_on_id) REFERENCES dependency_nodes(production_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TRIGGER source_assets_immutable BEFORE UPDATE ON source_assets
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER source_assets_retain BEFORE DELETE ON source_assets
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER text_revisions_immutable BEFORE UPDATE ON text_revisions
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER text_revisions_retain BEFORE DELETE ON text_revisions
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER source_spans_immutable BEFORE UPDATE ON source_spans
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER source_spans_retain BEFORE DELETE ON source_spans
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER content_units_immutable BEFORE UPDATE ON content_units
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER content_units_retain BEFORE DELETE ON content_units
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER text_mappings_immutable BEFORE UPDATE ON text_mappings
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER text_mappings_retain BEFORE DELETE ON text_mappings
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER production_scope_immutable BEFORE UPDATE ON production_scope
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER production_scope_retain BEFORE DELETE ON production_scope
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER scopes_immutable BEFORE UPDATE ON scopes
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER scopes_retain BEFORE DELETE ON scopes
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER scope_units_immutable BEFORE UPDATE ON scope_units
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER scope_units_retain BEFORE DELETE ON scope_units
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER result_receipts_immutable BEFORE UPDATE ON result_receipts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER result_receipts_retain BEFORE DELETE ON result_receipts
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER idempotency_receipts_immutable BEFORE UPDATE ON idempotency_receipts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER idempotency_receipts_retain BEFORE DELETE ON idempotency_receipts
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER checkpoints_immutable BEFORE UPDATE ON checkpoints
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER checkpoints_retain BEFORE DELETE ON checkpoints
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER checkpoint_units_immutable BEFORE UPDATE ON checkpoint_units
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER checkpoint_units_retain BEFORE DELETE ON checkpoint_units
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER synthesis_blocks_immutable BEFORE UPDATE ON synthesis_blocks
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER synthesis_blocks_retain BEFORE DELETE ON synthesis_blocks
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER sentence_links_immutable BEFORE UPDATE ON sentence_links
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER sentence_links_retain BEFORE DELETE ON sentence_links
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER review_records_immutable BEFORE UPDATE ON review_records
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER review_records_retain BEFORE DELETE ON review_records
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER audit_events_immutable BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER audit_events_retain BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER configurations_immutable BEFORE UPDATE ON configurations
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER configurations_retain BEFORE DELETE ON configurations
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER principals_immutable BEFORE UPDATE OF id,kind,created_at ON principals
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER artifacts_immutable BEFORE UPDATE OF id,sha256,size_bytes,media_type,created_at ON artifacts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER voice_versions_immutable BEFORE UPDATE OF id,voice_id,version,reference_artifact_id,reference_text,model_revisions_json,config_sha256,created_at ON voice_versions
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER voice_versions_retain BEFORE DELETE ON voice_versions
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER production_revisions_immutable BEFORE UPDATE OF id,book_id,text_revision_id,voice_version_id,model_revision,config_sha256,snapshot_sha256,created_at ON production_revisions
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER production_revisions_retain BEFORE DELETE ON production_revisions
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER tasks_immutable BEFORE UPDATE OF id,production_id,stage,unit_key,input_snapshot_sha256,created_at ON tasks
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER leases_immutable BEFORE UPDATE OF id,task_id,attempt_no,token_sha256,created_at ON leases
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER attempts_immutable BEFORE UPDATE OF task_id,attempt_no,worker_id,app_generation,input_snapshot_sha256,created_at ON attempts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

-- 人工记录与执行器回执的最小持久身份约束；HTTP授权仍另行检查。
CREATE TRIGGER worker_identity BEFORE INSERT ON workers
BEGIN SELECT RAISE(ABORT, '执行器必须关联执行器主体') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.principal_id AND kind='worker'); END;
CREATE TRIGGER session_identity BEFORE INSERT ON browser_sessions
BEGIN SELECT RAISE(ABORT, '会话必须关联用户主体') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.principal_id AND kind='human'); END;
CREATE TRIGGER token_identity BEFORE INSERT ON auth_tokens
BEGIN SELECT RAISE(ABORT, '令牌用途与主体不符') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.principal_id AND ((kind='worker' AND NEW.purpose='worker') OR (kind='human' AND NEW.purpose='cli'))); END;
CREATE TRIGGER review_voice_scope BEFORE INSERT ON review_records WHEN NEW.voice_version_id IS NOT NULL
BEGIN SELECT RAISE(ABORT, '声音试听范围不匹配') WHERE NOT EXISTS (
SELECT 1 FROM scopes WHERE id=NEW.scope_id AND voice_version_id=NEW.voice_version_id); END;
CREATE TRIGGER voice_starts_unapproved BEFORE INSERT ON voice_versions WHEN NEW.approved_review_id IS NOT NULL
BEGIN SELECT RAISE(ABORT, '声音版本必须先创建再登记认可'); END;
CREATE TRIGGER result_identity BEFORE INSERT ON result_receipts
BEGIN
SELECT RAISE(ABORT, '结果回执主体不属于执行尝试') WHERE NOT EXISTS (
SELECT 1 FROM attempts a JOIN workers w ON w.id=a.worker_id
WHERE a.task_id=NEW.task_id AND a.attempt_no=NEW.attempt_no AND w.principal_id=NEW.principal_id);
SELECT RAISE(ABORT, '结果不能引用未校验制品') WHERE EXISTS (
SELECT 1 FROM task_outputs o JOIN artifacts a ON a.id=o.artifact_id
WHERE o.task_id=NEW.task_id AND a.validation_status!='validated');
END;

CREATE TRIGGER pairing_identity BEFORE INSERT ON pairing_codes
BEGIN SELECT RAISE(ABORT, '配对码必须关联用户主体') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.principal_id AND kind='human'); END;
