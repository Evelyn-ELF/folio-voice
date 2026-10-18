-- 检测、证据、反馈、Agent、预算和交付历史。质量谓词与授权另由服务核验。

CREATE TABLE detector_bindings (
id TEXT PRIMARY KEY NOT NULL, version INTEGER NOT NULL CHECK(version>0), binding_sha256 TEXT NOT NULL CHECK ((length(binding_sha256) = 64 AND binding_sha256 NOT GLOB '*[^0-9a-f]*')),
descriptor_json TEXT NOT NULL CHECK (json_valid(descriptor_json) AND json_type(descriptor_json) = 'object'), CHECK(descriptor_json=fv_canonical_json(descriptor_json)), CHECK(binding_sha256=fv_config_hash(descriptor_json)),
CHECK(json_extract(descriptor_json,'$.id') IS id), CHECK(json_extract(descriptor_json,'$.version') IS version)
) STRICT;

CREATE TABLE compatibility_profiles (
id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0), deliverable_kind TEXT NOT NULL CHECK(deliverable_kind IN ('audio','epub')),
tested_versions_json TEXT NOT NULL CHECK (json_valid(tested_versions_json) AND json_type(tested_versions_json) = 'array'), file_features_json TEXT NOT NULL CHECK (json_valid(file_features_json) AND json_type(file_features_json) = 'array'), limits_json TEXT NOT NULL CHECK (json_valid(limits_json) AND json_type(limits_json) = 'object'),
status TEXT NOT NULL CHECK(status IN ('draft','active','suspended','revoked')), created_at TEXT NOT NULL, PRIMARY KEY(id,version)
) STRICT;

CREATE TABLE quality_snapshots (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
production_snapshot_sha256 TEXT NOT NULL CHECK ((length(production_snapshot_sha256) = 64 AND production_snapshot_sha256 NOT GLOB '*[^0-9a-f]*')), snapshot_sha256 TEXT NOT NULL CHECK ((length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*')), policy_hash TEXT REFERENCES policy_configs(policy_hash) ON DELETE RESTRICT,
report_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, qualification_id TEXT, qualification_version INTEGER,
compatibility_id TEXT, compatibility_version INTEGER, created_at TEXT NOT NULL, UNIQUE(production_id,revision), UNIQUE(id,production_id),
CHECK((qualification_id IS NULL)=(qualification_version IS NULL)), CHECK((compatibility_id IS NULL)=(compatibility_version IS NULL)),
FOREIGN KEY(production_id,production_snapshot_sha256) REFERENCES production_revisions(id,snapshot_sha256) ON DELETE RESTRICT,
FOREIGN KEY(qualification_id,qualification_version,policy_hash) REFERENCES qualification_versions(id,version,policy_hash) ON DELETE RESTRICT,
FOREIGN KEY(compatibility_id,compatibility_version) REFERENCES compatibility_profiles(id,version) ON DELETE RESTRICT
) STRICT;

CREATE TABLE gate_results (
quality_snapshot_id TEXT NOT NULL REFERENCES quality_snapshots(id) ON DELETE RESTRICT,
gate TEXT NOT NULL CHECK(gate IN ('Q1','Q2','Q3','Q4','Q5')), status TEXT NOT NULL CHECK(status IN ('pending','pass','blocked')),
PRIMARY KEY(quality_snapshot_id,gate)
) STRICT;

CREATE TABLE exports (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL, book_id TEXT NOT NULL, packaging_task_id TEXT NOT NULL,
candidate_kind TEXT NOT NULL CHECK(candidate_kind IN ('preview','formal_candidate')), deliverable_kind TEXT NOT NULL CHECK(deliverable_kind IN ('audio','epub')),
created_at TEXT NOT NULL, UNIQUE(id,production_id), UNIQUE(id,book_id), UNIQUE(id,deliverable_kind),
FOREIGN KEY(production_id,book_id) REFERENCES production_revisions(id,book_id) ON DELETE RESTRICT,
FOREIGN KEY(packaging_task_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE export_artifacts (
export_id TEXT NOT NULL REFERENCES exports(id) ON DELETE RESTRICT, artifact_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL CHECK ((length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*')),
PRIMARY KEY(export_id,artifact_id), UNIQUE(export_id,artifact_sha256), UNIQUE(export_id,artifact_id,artifact_sha256),
FOREIGN KEY(artifact_id,artifact_sha256) REFERENCES artifacts(id,sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE issues (
id TEXT PRIMARY KEY NOT NULL, book_id TEXT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
description TEXT NOT NULL CHECK(length(description)>0), severity TEXT NOT NULL CHECK(severity IN ('P0','P1','P2','P3')),
status TEXT NOT NULL CHECK(status IN ('awaiting_location','triaged','planned','candidate','awaiting_device_evidence','resolved_system','awaiting_feedback','closed_confirmed','reopened','withdrawn')),
revision INTEGER NOT NULL CHECK(revision>0), reported_export_id TEXT, reported_artifact_sha256 TEXT CHECK (reported_artifact_sha256 IS NULL OR (length(reported_artifact_sha256) = 64 AND reported_artifact_sha256 NOT GLOB '*[^0-9a-f]*')),
scope_id TEXT REFERENCES scopes(id) ON DELETE RESTRICT, environment_json TEXT CHECK (environment_json IS NULL OR (json_valid(environment_json) AND json_type(environment_json) = 'object')), created_at TEXT NOT NULL,
UNIQUE(id,book_id), CHECK((reported_export_id IS NULL)=(reported_artifact_sha256 IS NULL)),
FOREIGN KEY(reported_export_id,book_id) REFERENCES exports(id,book_id) ON DELETE RESTRICT,
FOREIGN KEY(reported_export_id,reported_artifact_sha256) REFERENCES export_artifacts(export_id,artifact_sha256) ON DELETE RESTRICT,
FOREIGN KEY(id,revision) REFERENCES issue_revisions(issue_id,revision) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
) STRICT;

CREATE TABLE issue_revisions (
issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE RESTRICT, revision INTEGER NOT NULL CHECK(revision>0),
snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json) AND json_type(snapshot_json) = 'object'), created_at TEXT NOT NULL, PRIMARY KEY(issue_id,revision),
CHECK(json_extract(snapshot_json,'$.id') IS issue_id), CHECK(json_extract(snapshot_json,'$.revision') IS revision)
) STRICT;

CREATE TABLE repair_plans (
id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0), issue_id TEXT NOT NULL, issue_revision INTEGER NOT NULL,
book_id TEXT NOT NULL, base_export_id TEXT NOT NULL, base_artifact_sha256 TEXT NOT NULL CHECK ((length(base_artifact_sha256) = 64 AND base_artifact_sha256 NOT GLOB '*[^0-9a-f]*')), target_production_id TEXT NOT NULL,
retest_cases_json TEXT NOT NULL CHECK (json_valid(retest_cases_json) AND json_type(retest_cases_json) = 'array'), required_environment_json TEXT CHECK (required_environment_json IS NULL OR (json_valid(required_environment_json) AND json_type(required_environment_json) = 'object')), created_at TEXT NOT NULL,
PRIMARY KEY(id,version), UNIQUE(id,version,issue_id), UNIQUE(id,version,target_production_id),
FOREIGN KEY(issue_id,issue_revision) REFERENCES issue_revisions(issue_id,revision) ON DELETE RESTRICT,
FOREIGN KEY(issue_id,book_id) REFERENCES issues(id,book_id) ON DELETE RESTRICT,
FOREIGN KEY(base_export_id,book_id) REFERENCES exports(id,book_id) ON DELETE RESTRICT,
FOREIGN KEY(base_export_id,base_artifact_sha256) REFERENCES export_artifacts(export_id,artifact_sha256) ON DELETE RESTRICT,
FOREIGN KEY(target_production_id,book_id) REFERENCES production_revisions(id,book_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE repair_plan_nodes (
plan_id TEXT NOT NULL, plan_version INTEGER NOT NULL, production_id TEXT NOT NULL, node_id TEXT NOT NULL,
effect TEXT NOT NULL CHECK(effect IN ('changed','invalidated','retained')), PRIMARY KEY(plan_id,plan_version,node_id),
FOREIGN KEY(plan_id,plan_version,production_id) REFERENCES repair_plans(id,version,target_production_id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,node_id) REFERENCES dependency_nodes(production_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE repair_plan_rollbacks (
plan_id TEXT NOT NULL, plan_version INTEGER NOT NULL, artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
PRIMARY KEY(plan_id,plan_version,artifact_id), FOREIGN KEY(plan_id,plan_version) REFERENCES repair_plans(id,version) ON DELETE RESTRICT
) STRICT;

CREATE TABLE evidence_records (
server_sequence INTEGER PRIMARY KEY AUTOINCREMENT CHECK(server_sequence>0), id TEXT NOT NULL UNIQUE,
contract_version INTEGER NOT NULL DEFAULT 2 CHECK(contract_version=2), production_id TEXT NOT NULL REFERENCES production_revisions(id) ON DELETE RESTRICT,
input_artifact_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL CHECK ((length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*')), binding_id TEXT REFERENCES detector_bindings(id) ON DELETE RESTRICT,
scope_id TEXT NOT NULL, risk TEXT CHECK(risk IN ('D01','D02','D03','D04','D05','D06')),
outcome TEXT NOT NULL CHECK(outcome IN ('pass','suspect','fail','unknown','error')),
evidence_kind TEXT NOT NULL CHECK(evidence_kind IN ('tool','human','device_test','compatibility_match')),
actor_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT, gate TEXT NOT NULL CHECK(gate IN ('Q1','Q2','Q3','Q4','Q5')),
case_id TEXT NOT NULL, rule_version TEXT NOT NULL, environment_json TEXT CHECK (environment_json IS NULL OR (json_valid(environment_json) AND json_type(environment_json) = 'object')),
issue_id TEXT, issue_revision INTEGER, plan_id TEXT, plan_version INTEGER, created_at TEXT NOT NULL,
UNIQUE(id,input_artifact_id,artifact_sha256), UNIQUE(id,production_id), UNIQUE(id,issue_id), UNIQUE(id,production_id,gate), UNIQUE(id,gate),
CHECK(evidence_kind!='tool' OR binding_id IS NOT NULL),
CHECK((issue_id IS NULL AND issue_revision IS NULL AND plan_id IS NULL AND plan_version IS NULL)
OR (issue_id IS NOT NULL AND issue_revision IS NOT NULL AND plan_id IS NOT NULL AND plan_version IS NOT NULL)),
FOREIGN KEY(input_artifact_id,artifact_sha256) REFERENCES artifacts(id,sha256) ON DELETE RESTRICT,
FOREIGN KEY(production_id,scope_id) REFERENCES scopes(production_id,id) ON DELETE RESTRICT,
FOREIGN KEY(issue_id,issue_revision) REFERENCES issue_revisions(issue_id,revision) ON DELETE RESTRICT,
FOREIGN KEY(plan_id,plan_version,issue_id) REFERENCES repair_plans(id,version,issue_id) ON DELETE RESTRICT,
FOREIGN KEY(plan_id,plan_version,production_id) REFERENCES repair_plans(id,version,target_production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE evidence_intervals (
evidence_id TEXT NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT,
start_sample INTEGER NOT NULL CHECK(start_sample>=0), end_sample INTEGER NOT NULL CHECK(end_sample>start_sample),
sample_rate INTEGER NOT NULL CHECK(sample_rate>0), PRIMARY KEY(evidence_id,start_sample,end_sample,sample_rate)
) STRICT;

CREATE TABLE evidence_attachments (
evidence_id TEXT NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, PRIMARY KEY(evidence_id,artifact_id)
) STRICT;

CREATE TABLE gate_evidence (
quality_snapshot_id TEXT NOT NULL, gate TEXT NOT NULL, evidence_id TEXT NOT NULL,
production_id TEXT NOT NULL, PRIMARY KEY(quality_snapshot_id,gate,evidence_id),
FOREIGN KEY(quality_snapshot_id,gate) REFERENCES gate_results(quality_snapshot_id,gate) ON DELETE RESTRICT,
FOREIGN KEY(quality_snapshot_id,production_id) REFERENCES quality_snapshots(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(evidence_id,production_id,gate) REFERENCES evidence_records(id,production_id,gate) ON DELETE RESTRICT
) STRICT;

CREATE TABLE compatibility_device_tests (
profile_id TEXT NOT NULL, profile_version INTEGER NOT NULL, evidence_id TEXT NOT NULL,
artifact_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL CHECK ((length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*')), PRIMARY KEY(profile_id,profile_version,evidence_id),
FOREIGN KEY(profile_id,profile_version) REFERENCES compatibility_profiles(id,version) ON DELETE RESTRICT,
FOREIGN KEY(evidence_id,artifact_id,artifact_sha256) REFERENCES evidence_records(id,input_artifact_id,artifact_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE findings (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL, scope_id TEXT NOT NULL,
risk TEXT NOT NULL CHECK(risk IN ('D01','D02','D03','D04','D05','D06')),
status TEXT NOT NULL CHECK(status IN ('open','confirmed','false_positive','repaired')),
baseline_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
candidate_artifact_id TEXT REFERENCES artifacts(id) ON DELETE RESTRICT, adjudication_rule_sha256 TEXT, created_at TEXT NOT NULL,
UNIQUE(id,production_id), FOREIGN KEY(production_id,scope_id) REFERENCES scopes(production_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE finding_evidence (
finding_id TEXT NOT NULL, evidence_id TEXT NOT NULL, production_id TEXT NOT NULL,
PRIMARY KEY(finding_id,evidence_id), FOREIGN KEY(finding_id,production_id) REFERENCES findings(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(evidence_id,production_id) REFERENCES evidence_records(id,production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE repair_proofs (
id TEXT PRIMARY KEY NOT NULL, issue_id TEXT NOT NULL, plan_id TEXT NOT NULL, plan_version INTEGER NOT NULL,
candidate_artifact_id TEXT NOT NULL, candidate_sha256 TEXT NOT NULL CHECK ((length(candidate_sha256) = 64 AND candidate_sha256 NOT GLOB '*[^0-9a-f]*')), reproduction_evidence_id TEXT NOT NULL,
quality_snapshot_id TEXT NOT NULL, production_id TEXT NOT NULL, created_at TEXT NOT NULL,
UNIQUE(id,issue_id,plan_id,plan_version,candidate_artifact_id,candidate_sha256),
FOREIGN KEY(plan_id,plan_version,issue_id) REFERENCES repair_plans(id,version,issue_id) ON DELETE RESTRICT,
FOREIGN KEY(plan_id,plan_version,production_id) REFERENCES repair_plans(id,version,target_production_id) ON DELETE RESTRICT,
FOREIGN KEY(quality_snapshot_id,production_id) REFERENCES quality_snapshots(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(reproduction_evidence_id,issue_id) REFERENCES evidence_records(id,issue_id) ON DELETE RESTRICT,
FOREIGN KEY(reproduction_evidence_id,candidate_artifact_id,candidate_sha256) REFERENCES evidence_records(id,input_artifact_id,artifact_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE proof_evidence (
proof_id TEXT NOT NULL REFERENCES repair_proofs(id) ON DELETE RESTRICT,
evidence_id TEXT NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT, PRIMARY KEY(proof_id,evidence_id)
) STRICT;

CREATE TABLE resolution_records (
id TEXT PRIMARY KEY NOT NULL, issue_id TEXT NOT NULL, issue_revision INTEGER NOT NULL,
plan_id TEXT NOT NULL, plan_version INTEGER NOT NULL, candidate_artifact_id TEXT NOT NULL, candidate_sha256 TEXT NOT NULL CHECK ((length(candidate_sha256) = 64 AND candidate_sha256 NOT GLOB '*[^0-9a-f]*')),
proof_id TEXT NOT NULL, resolution_kind TEXT NOT NULL CHECK(resolution_kind IN ('resolved_system','awaiting_feedback')),
created_at TEXT NOT NULL, UNIQUE(id,issue_id), UNIQUE(id,issue_id,candidate_artifact_id,candidate_sha256),
FOREIGN KEY(issue_id,issue_revision) REFERENCES issue_revisions(issue_id,revision) ON DELETE RESTRICT,
FOREIGN KEY(proof_id,issue_id,plan_id,plan_version,candidate_artifact_id,candidate_sha256)
REFERENCES repair_proofs(id,issue_id,plan_id,plan_version,candidate_artifact_id,candidate_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE resolution_invalidations (
id TEXT PRIMARY KEY NOT NULL, resolution_id TEXT NOT NULL REFERENCES resolution_records(id) ON DELETE RESTRICT,
evidence_id TEXT NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT, reason TEXT NOT NULL, created_at TEXT NOT NULL
) STRICT;

CREATE TABLE issue_applicability (
id TEXT PRIMARY KEY NOT NULL, issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE RESTRICT,
candidate_artifact_id TEXT NOT NULL, candidate_sha256 TEXT NOT NULL CHECK ((length(candidate_sha256) = 64 AND candidate_sha256 NOT GLOB '*[^0-9a-f]*')), scope_id TEXT NOT NULL REFERENCES scopes(id) ON DELETE RESTRICT,
environment_json TEXT NOT NULL CHECK (json_valid(environment_json) AND json_type(environment_json) = 'object'), resolution_id TEXT, UNIQUE(issue_id,candidate_artifact_id,scope_id,environment_json),
FOREIGN KEY(candidate_artifact_id,candidate_sha256) REFERENCES artifacts(id,sha256) ON DELETE RESTRICT,
FOREIGN KEY(resolution_id,issue_id,candidate_artifact_id,candidate_sha256)
REFERENCES resolution_records(id,issue_id,candidate_artifact_id,candidate_sha256) ON DELETE RESTRICT
) STRICT;

CREATE TABLE issue_confirmations (
id TEXT PRIMARY KEY NOT NULL, issue_id TEXT NOT NULL REFERENCES issues(id) ON DELETE RESTRICT,
resolution_id TEXT NOT NULL,
actor_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT, feedback TEXT NOT NULL CHECK(length(feedback)>0), created_at TEXT NOT NULL,
FOREIGN KEY(resolution_id,issue_id) REFERENCES resolution_records(id,issue_id) ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX qualification_event_release_key ON qualification_events(qualification_id,qualification_version,revision,revocation_sequence);

CREATE TABLE release_decisions (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
request_id TEXT NOT NULL, payload_sha256 TEXT NOT NULL CHECK ((length(payload_sha256) = 64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*')), export_id TEXT NOT NULL, artifact_id TEXT NOT NULL, artifact_sha256 TEXT NOT NULL CHECK ((length(artifact_sha256) = 64 AND artifact_sha256 NOT GLOB '*[^0-9a-f]*')),
deliverable_kind TEXT NOT NULL CHECK(deliverable_kind IN ('audio','epub')), production_id TEXT NOT NULL,
quality_snapshot_id TEXT NOT NULL, qualification_id TEXT, qualification_version INTEGER, qualification_event_revision INTEGER,
revocation_sequence INTEGER, compatibility_id TEXT, compatibility_version INTEGER,
decision TEXT NOT NULL CHECK(decision IN ('released','blocked')), blockers_json TEXT NOT NULL CHECK (json_valid(blockers_json) AND json_type(blockers_json) = 'array'), created_at TEXT NOT NULL,
UNIQUE(principal_id,request_id), UNIQUE(id,quality_snapshot_id,production_id),
CHECK((decision='released' AND qualification_id IS NOT NULL AND qualification_version IS NOT NULL AND qualification_event_revision IS NOT NULL
AND revocation_sequence IS NOT NULL AND compatibility_id IS NOT NULL AND compatibility_version IS NOT NULL AND json_array_length(blockers_json)=0)
OR (decision='blocked' AND json_array_length(blockers_json)>0)),
FOREIGN KEY(export_id,production_id) REFERENCES exports(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(export_id,deliverable_kind) REFERENCES exports(id,deliverable_kind) ON DELETE RESTRICT,
FOREIGN KEY(export_id,artifact_id,artifact_sha256) REFERENCES export_artifacts(export_id,artifact_id,artifact_sha256) ON DELETE RESTRICT,
FOREIGN KEY(quality_snapshot_id,production_id) REFERENCES quality_snapshots(id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(qualification_id,qualification_version,qualification_event_revision,revocation_sequence)
REFERENCES qualification_events(qualification_id,qualification_version,revision,revocation_sequence) ON DELETE RESTRICT,
FOREIGN KEY(compatibility_id,compatibility_version) REFERENCES compatibility_profiles(id,version) ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX released_delivery_key ON release_decisions(export_id,artifact_id,deliverable_kind,quality_snapshot_id) WHERE decision='released';

CREATE TABLE release_gate_evidence (
release_id TEXT NOT NULL, quality_snapshot_id TEXT NOT NULL, production_id TEXT NOT NULL,
gate TEXT NOT NULL CHECK(gate IN ('Q1','Q2','Q3','Q4','Q5')), evidence_id TEXT NOT NULL,
PRIMARY KEY(release_id,gate,evidence_id),
FOREIGN KEY(release_id,quality_snapshot_id,production_id) REFERENCES release_decisions(id,quality_snapshot_id,production_id) ON DELETE RESTRICT,
FOREIGN KEY(quality_snapshot_id,gate,evidence_id) REFERENCES gate_evidence(quality_snapshot_id,gate,evidence_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE release_risk_events (
id INTEGER PRIMARY KEY AUTOINCREMENT, release_id TEXT NOT NULL REFERENCES release_decisions(id) ON DELETE RESTRICT,
qualification_id TEXT NOT NULL, qualification_version INTEGER NOT NULL, qualification_event_revision INTEGER NOT NULL, revocation_sequence INTEGER NOT NULL,
reason TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(release_id,revocation_sequence),
FOREIGN KEY(qualification_id,qualification_version,qualification_event_revision,revocation_sequence)
REFERENCES qualification_events(qualification_id,qualification_version,revision,revocation_sequence) ON DELETE RESTRICT
) STRICT;

CREATE TRIGGER qualification_release_risk AFTER INSERT ON qualification_events WHEN NEW.status IN ('suspended','revoked')
BEGIN INSERT INTO release_risk_events(release_id,qualification_id,qualification_version,qualification_event_revision,revocation_sequence,reason,created_at)
SELECT id,NEW.qualification_id,NEW.qualification_version,NEW.revision,NEW.revocation_sequence,NEW.reason,NEW.created_at
FROM release_decisions WHERE qualification_id=NEW.qualification_id AND qualification_version=NEW.qualification_version AND decision='released'; END;

CREATE TABLE agent_runs (
id TEXT PRIMARY KEY NOT NULL, production_id TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL CHECK ((length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*')),
policy_hash TEXT REFERENCES policy_configs(policy_hash) ON DELETE RESTRICT, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
scope_id TEXT NOT NULL, provider_id TEXT NOT NULL, model_revision TEXT NOT NULL, template_version TEXT NOT NULL, schema_version TEXT NOT NULL,
state TEXT NOT NULL CHECK(state IN ('queued','running','waiting_tool','waiting_provider','budget_exhausted','needs_input','cancelled','no_progress','stale','needs_maintenance','completed')),
created_at TEXT NOT NULL, UNIQUE(id,production_id,principal_id), FOREIGN KEY(production_id,snapshot_sha256) REFERENCES production_revisions(id,snapshot_sha256) ON DELETE RESTRICT,
FOREIGN KEY(production_id,scope_id) REFERENCES scopes(production_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE agent_steps (
run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE RESTRICT, step_sequence INTEGER NOT NULL CHECK(step_sequence>0),
decision_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, created_at TEXT NOT NULL, PRIMARY KEY(run_id,step_sequence)
) STRICT;

CREATE TABLE tool_receipts (
id TEXT PRIMARY KEY NOT NULL, run_id TEXT NOT NULL, step_sequence INTEGER NOT NULL,
principal_id TEXT NOT NULL, production_id TEXT NOT NULL, action_key TEXT NOT NULL CHECK(length(action_key)>0),
tool_version TEXT NOT NULL, payload_sha256 TEXT NOT NULL CHECK ((length(payload_sha256) = 64 AND payload_sha256 NOT GLOB '*[^0-9a-f]*')), task_id TEXT, result_json TEXT NOT NULL CHECK (json_valid(result_json) AND json_type(result_json) = 'object'), created_at TEXT NOT NULL,
UNIQUE(principal_id,production_id,action_key), FOREIGN KEY(run_id,step_sequence) REFERENCES agent_steps(run_id,step_sequence) ON DELETE RESTRICT,
FOREIGN KEY(run_id,production_id,principal_id) REFERENCES agent_runs(id,production_id,principal_id) ON DELETE RESTRICT,
FOREIGN KEY(task_id,production_id) REFERENCES tasks(id,production_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE tool_receipt_artifacts (
receipt_id TEXT NOT NULL REFERENCES tool_receipts(id) ON DELETE RESTRICT,
artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, PRIMARY KEY(receipt_id,artifact_id)
) STRICT;

CREATE TABLE repair_proposals (
id TEXT PRIMARY KEY NOT NULL, run_id TEXT NOT NULL, production_id TEXT NOT NULL, principal_id TEXT NOT NULL,
revision INTEGER NOT NULL CHECK(revision>0), scope_id TEXT NOT NULL,
baseline_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
candidate_artifact_id TEXT REFERENCES artifacts(id) ON DELETE RESTRICT,
actions_artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT, created_at TEXT NOT NULL,
FOREIGN KEY(run_id,production_id,principal_id) REFERENCES agent_runs(id,production_id,principal_id) ON DELETE RESTRICT,
FOREIGN KEY(production_id,scope_id) REFERENCES scopes(production_id,id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget_accounts (
id TEXT PRIMARY KEY NOT NULL, principal_id TEXT NOT NULL REFERENCES principals(id) ON DELETE RESTRICT,
currency TEXT NOT NULL CHECK(length(currency)=3 AND currency NOT GLOB '*[^A-Z]*'), timezone TEXT NOT NULL,
daily_limit_minor INTEGER NOT NULL CHECK(daily_limit_minor>=0), created_at TEXT NOT NULL, UNIQUE(id,currency)
) STRICT;

CREATE TABLE production_budgets (
production_id TEXT PRIMARY KEY NOT NULL REFERENCES production_revisions(id) ON DELETE RESTRICT,
account_id TEXT NOT NULL REFERENCES budget_accounts(id) ON DELETE RESTRICT, limit_minor INTEGER NOT NULL CHECK(limit_minor>=0),
UNIQUE(production_id,account_id)
) STRICT;

CREATE TABLE budget_ledger (
id TEXT PRIMARY KEY NOT NULL, account_id TEXT NOT NULL, production_id TEXT NOT NULL,
call_id TEXT NOT NULL CHECK(length(call_id)>0), entry_kind TEXT NOT NULL CHECK(entry_kind IN ('reserve','unknown','settle')),
amount_minor INTEGER NOT NULL CHECK(amount_minor>=0), currency TEXT NOT NULL, local_day TEXT NOT NULL CHECK(date(local_day) IS local_day),
created_at TEXT NOT NULL, UNIQUE(account_id,production_id,call_id,entry_kind),
FOREIGN KEY(account_id,currency) REFERENCES budget_accounts(id,currency) ON DELETE RESTRICT,
FOREIGN KEY(production_id,account_id) REFERENCES production_budgets(production_id,account_id) ON DELETE RESTRICT
) STRICT;

CREATE VIEW budget_exposure AS SELECT r.account_id,r.production_id,r.call_id,r.local_day,r.currency,
coalesce(s.amount_minor,r.amount_minor) AS amount_minor FROM budget_ledger AS r
LEFT JOIN budget_ledger AS s ON s.account_id=r.account_id AND s.production_id=r.production_id AND s.call_id=r.call_id AND s.entry_kind='settle'
WHERE r.entry_kind='reserve';

CREATE TRIGGER budget_entry_integrity BEFORE INSERT ON budget_ledger
BEGIN
SELECT RAISE(ABORT, '结算或未知费用必须匹配预留') WHERE NEW.entry_kind!='reserve' AND NOT EXISTS (
SELECT 1 FROM budget_ledger WHERE account_id=NEW.account_id AND production_id=NEW.production_id AND call_id=NEW.call_id
AND entry_kind='reserve' AND local_day=NEW.local_day AND currency=NEW.currency
AND (NEW.entry_kind!='unknown' OR amount_minor=NEW.amount_minor));
SELECT RAISE(ABORT, '已结算调用不能再记未知费用') WHERE NEW.entry_kind='unknown' AND EXISTS (
SELECT 1 FROM budget_ledger WHERE account_id=NEW.account_id AND production_id=NEW.production_id AND call_id=NEW.call_id AND entry_kind='settle');
SELECT RAISE(ABORT, '制作预算不足') WHERE NEW.entry_kind='reserve' AND NEW.amount_minor+coalesce((
SELECT sum(amount_minor) FROM budget_exposure WHERE production_id=NEW.production_id),0)>(
SELECT limit_minor FROM production_budgets WHERE production_id=NEW.production_id AND account_id=NEW.account_id);
SELECT RAISE(ABORT, '每日预算不足') WHERE NEW.entry_kind='reserve' AND NEW.amount_minor+coalesce((
SELECT sum(amount_minor) FROM budget_exposure WHERE account_id=NEW.account_id AND local_day=NEW.local_day),0)>(
SELECT daily_limit_minor FROM budget_accounts WHERE id=NEW.account_id);
END;

CREATE TRIGGER issue_confirmations_human BEFORE INSERT ON issue_confirmations 
BEGIN SELECT RAISE(ABORT, '人工或真机记录需用户身份') WHERE NOT EXISTS (SELECT 1 FROM principals WHERE id=NEW.actor_id AND kind='human'); END;

CREATE TRIGGER evidence_records_human BEFORE INSERT ON evidence_records WHEN NEW.evidence_kind IN ('human','device_test')
BEGIN SELECT RAISE(ABORT, '人工或真机记录需用户身份') WHERE NOT EXISTS (SELECT 1 FROM principals WHERE id=NEW.actor_id AND kind='human'); END;

CREATE TRIGGER detector_bindings_immutable BEFORE UPDATE ON detector_bindings
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER detector_bindings_retain BEFORE DELETE ON detector_bindings
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER quality_snapshots_immutable BEFORE UPDATE ON quality_snapshots
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER quality_snapshots_retain BEFORE DELETE ON quality_snapshots
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER gate_results_immutable BEFORE UPDATE ON gate_results
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER gate_results_retain BEFORE DELETE ON gate_results
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER gate_evidence_immutable BEFORE UPDATE ON gate_evidence
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER gate_evidence_retain BEFORE DELETE ON gate_evidence
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER compatibility_device_tests_immutable BEFORE UPDATE ON compatibility_device_tests
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER compatibility_device_tests_retain BEFORE DELETE ON compatibility_device_tests
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER finding_evidence_immutable BEFORE UPDATE ON finding_evidence
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER finding_evidence_retain BEFORE DELETE ON finding_evidence
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER issue_revisions_immutable BEFORE UPDATE ON issue_revisions
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER issue_revisions_retain BEFORE DELETE ON issue_revisions
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER repair_plans_immutable BEFORE UPDATE ON repair_plans
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER repair_plans_retain BEFORE DELETE ON repair_plans
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER repair_plan_nodes_immutable BEFORE UPDATE ON repair_plan_nodes
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER repair_plan_nodes_retain BEFORE DELETE ON repair_plan_nodes
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER repair_plan_rollbacks_immutable BEFORE UPDATE ON repair_plan_rollbacks
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER repair_plan_rollbacks_retain BEFORE DELETE ON repair_plan_rollbacks
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER evidence_records_immutable BEFORE UPDATE ON evidence_records
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER evidence_records_retain BEFORE DELETE ON evidence_records
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER evidence_intervals_immutable BEFORE UPDATE ON evidence_intervals
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER evidence_intervals_retain BEFORE DELETE ON evidence_intervals
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER evidence_attachments_immutable BEFORE UPDATE ON evidence_attachments
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER evidence_attachments_retain BEFORE DELETE ON evidence_attachments
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER repair_proofs_immutable BEFORE UPDATE ON repair_proofs
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER repair_proofs_retain BEFORE DELETE ON repair_proofs
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER proof_evidence_immutable BEFORE UPDATE ON proof_evidence
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER proof_evidence_retain BEFORE DELETE ON proof_evidence
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER resolution_records_immutable BEFORE UPDATE ON resolution_records
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER resolution_records_retain BEFORE DELETE ON resolution_records
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER resolution_invalidations_immutable BEFORE UPDATE ON resolution_invalidations
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER resolution_invalidations_retain BEFORE DELETE ON resolution_invalidations
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER issue_confirmations_immutable BEFORE UPDATE ON issue_confirmations
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER issue_confirmations_retain BEFORE DELETE ON issue_confirmations
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER exports_immutable BEFORE UPDATE ON exports
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER exports_retain BEFORE DELETE ON exports
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER export_artifacts_immutable BEFORE UPDATE ON export_artifacts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER export_artifacts_retain BEFORE DELETE ON export_artifacts
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER release_decisions_immutable BEFORE UPDATE ON release_decisions
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER release_decisions_retain BEFORE DELETE ON release_decisions
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER release_gate_evidence_immutable BEFORE UPDATE ON release_gate_evidence
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER release_gate_evidence_retain BEFORE DELETE ON release_gate_evidence
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER release_risk_events_immutable BEFORE UPDATE ON release_risk_events
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER release_risk_events_retain BEFORE DELETE ON release_risk_events
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER agent_steps_immutable BEFORE UPDATE ON agent_steps
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER agent_steps_retain BEFORE DELETE ON agent_steps
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER tool_receipts_immutable BEFORE UPDATE ON tool_receipts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER tool_receipts_retain BEFORE DELETE ON tool_receipts
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER tool_receipt_artifacts_immutable BEFORE UPDATE ON tool_receipt_artifacts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER tool_receipt_artifacts_retain BEFORE DELETE ON tool_receipt_artifacts
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER repair_proposals_immutable BEFORE UPDATE ON repair_proposals
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER repair_proposals_retain BEFORE DELETE ON repair_proposals
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER budget_ledger_immutable BEFORE UPDATE ON budget_ledger
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER budget_ledger_retain BEFORE DELETE ON budget_ledger
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER compatibility_profiles_immutable BEFORE UPDATE OF id,version,deliverable_kind,tested_versions_json,file_features_json,limits_json,created_at ON compatibility_profiles
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER compatibility_profiles_retain BEFORE DELETE ON compatibility_profiles
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER budget_accounts_immutable BEFORE UPDATE OF id,principal_id,currency,timezone,created_at ON budget_accounts
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER issues_immutable BEFORE UPDATE OF id,book_id,description,created_at ON issues
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER issues_retain BEFORE DELETE ON issues
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

CREATE TRIGGER agent_runs_immutable BEFORE UPDATE OF id,production_id,snapshot_sha256,policy_hash,principal_id,scope_id,provider_id,model_revision,template_version,schema_version,created_at ON agent_runs
BEGIN SELECT RAISE(ABORT, '历史或冻结字段不可覆盖'); END;

CREATE TRIGGER agent_runs_retain BEFORE DELETE ON agent_runs
BEGIN SELECT RAISE(ABORT, '历史记录只可追加'); END;

-- 证据变化递增制作质量版本；历史快照和交付仍保留。
CREATE TRIGGER evidence_quality_revision AFTER INSERT ON evidence_records
BEGIN UPDATE production_revisions SET quality_revision=quality_revision+1 WHERE id=NEW.production_id; END;
CREATE TRIGGER issue_revision_monotonic BEFORE UPDATE ON issues WHEN NEW.revision!=OLD.revision+1
BEGIN SELECT RAISE(ABORT, '问题更新必须递增版本'); END;
CREATE TRIGGER issue_history_monotonic BEFORE INSERT ON issue_revisions
WHEN NEW.revision!=coalesce((SELECT max(revision) FROM issue_revisions WHERE issue_id=NEW.issue_id),0)+1
BEGIN SELECT RAISE(ABORT, '问题历史版本必须连续'); END;
CREATE TRIGGER release_storage_guards BEFORE INSERT ON release_decisions WHEN NEW.decision='released'
BEGIN
SELECT RAISE(ABORT, '交付必须由用户主体登记') WHERE NOT EXISTS (
SELECT 1 FROM principals WHERE id=NEW.principal_id AND kind='human');
SELECT RAISE(ABORT, '交付质量版本或资格配置失效') WHERE NOT EXISTS (
SELECT 1 FROM quality_snapshots q JOIN production_revisions p ON p.id=q.production_id
JOIN current_qualifications c ON c.id=NEW.qualification_id AND c.version=NEW.qualification_version
JOIN compatibility_profiles cp ON cp.id=NEW.compatibility_id AND cp.version=NEW.compatibility_version
WHERE q.id=NEW.quality_snapshot_id AND p.id=NEW.production_id AND q.revision=p.quality_revision
AND q.policy_hash=c.policy_hash AND c.status='active' AND c.revocation_sequence=NEW.revocation_sequence
AND c.revision=NEW.qualification_event_revision AND q.qualification_id=c.id AND q.qualification_version=c.version
AND q.compatibility_id=cp.id AND q.compatibility_version=cp.version AND cp.status='active' AND cp.deliverable_kind=NEW.deliverable_kind);
SELECT RAISE(ABORT, '交付门槛记录或证据缺失') WHERE (SELECT count(*) FROM gate_results
WHERE quality_snapshot_id=NEW.quality_snapshot_id AND status='pass')!=5
OR (SELECT count(DISTINCT gate) FROM gate_evidence WHERE quality_snapshot_id=NEW.quality_snapshot_id)!=5;
END;
