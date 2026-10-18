// 自动生成，请勿手改；运行约束、条件与权限须另按源Schema及服务规则验证。
export const SCHEMA_SHA256 = "ae5453e3fb698de9c8659051fc515f784d091525cd95bc964f3af38469b6954b";

export type UUID = string;

export type SHA256 = string;

export type Action = {
  "tool": "get_evidence" | "inspect_source" | "compare_stages" | "run_detector" | "submit_repair";
  "resource_ids": Array<UUID>;
  "binding_id": UUID | null;
};

export type PlanStep = {
  "step_id": number;
  "goal": string;
  "expected_evidence": string;
};

export type AgentDecision = {
  "run_id": UUID;
  "snapshot_hash": SHA256;
  "plan_revision": number;
  "decision": "observe" | "propose_repair" | "stop";
  "reason_summary": string;
  "evidence_ids": Array<UUID>;
  "plan_steps": Array<PlanStep>;
  "action": Action | null;
  "stop_reason": "complete" | "no_progress" | "budget_exhausted" | "needs_input" | "needs_maintenance" | "stale" | "cancelled" | null;
};

export type Interval = {
  "start_sample": number;
  "end_sample": number;
};

export type Evidence = {
  "id": UUID;
  "contract_version": 2;
  "snapshot_hash": SHA256;
  "artifact_sha256": SHA256;
  "binding_id": UUID;
  "scope_id": UUID;
  "risk": "D01" | "D02" | "D03" | "D04" | "D05" | "D06";
  "outcome": "pass" | "suspect" | "fail" | "unknown" | "error";
  "intervals": Array<Interval>;
  "attachment_ids": Array<UUID>;
  "server_sequence": number;
};

export type ResolveCommand = {
  "request_id": UUID;
  "issue_id": UUID;
  "issue_revision": number;
  "candidate_sha256": SHA256;
  "proof_id": UUID;
  "quality_revision": number;
  "contract_version": 2;
};

export type ReleaseCommand = {
  "request_id": UUID;
  "artifact_id": UUID;
  "artifact_sha256": SHA256;
  "deliverable_kind": "audio" | "epub";
  "quality_revision": number;
  "contract_version": 2;
};

export type CandidateSelection = {
  "baseline_sha256": SHA256;
  "candidate_sha256": SHA256;
  "policy_sha256": SHA256;
  "target_finding_ids": Array<UUID>;
  "comparison_evidence_ids": Array<UUID>;
  "decision": "provisional" | "final" | "reject";
  "reason_codes": Array<"target_unresolved" | "new_defect" | "regression" | "missing_evidence" | "scope_mismatch" | "all_checks_passed" | "lower_rebuild_cost">;
};

export type DateTime = string;

export type ArtifactReference = {
  "artifact_id": UUID;
  "size_bytes": number;
  "sha256": SHA256;
};

export type CreateProduction = {
  "book_id": UUID;
  "text_revision_id": UUID;
  "voice_version_id": UUID;
  "model_revision": string;
  "config_sha256": SHA256;
  "scope": Array<UUID>;
  "request_id": UUID;
};

export type ProductionAccepted = {
  "production_id": UUID;
  "control_revision": number;
  "status_url": string;
};

export type TaskLease = {
  "task_id": UUID;
  "production_id": UUID;
  "attempt_no": number;
  "lease_token": string;
  "input_snapshot_sha256": SHA256;
  "app_generation": UUID;
  "expires_at": DateTime;
  "control_revision": number;
  "input_artifacts": Array<ArtifactReference>;
};

export type Heartbeat = {
  "attempt_no": number;
  "lease_token": string;
  "input_snapshot_sha256": SHA256;
  "app_generation": UUID;
};

export type CheckpointCommand = {
  "request_id": UUID;
  "attempt_no": number;
  "lease_token": string;
  "input_snapshot_sha256": SHA256;
  "app_generation": UUID;
  "checkpoint_artifact_id": UUID;
  "completed_unit_ids": Array<UUID>;
};

export type TaskResult = {
  "request_id": UUID;
  "attempt_no": number;
  "lease_token": string;
  "input_snapshot_sha256": SHA256;
  "app_generation": UUID;
  "output_artifact_ids": Array<UUID>;
  "result_summary": string;
};

export type ProductionControl = {
  "request_id": UUID;
  "expected_control_revision": number;
};

export type CheckpointUnitArtifacts = {
  "unit_id": UUID;
  "artifacts": Array<ArtifactReference>;
};

export type CheckpointManifest = {
  "input_snapshot_sha256": SHA256;
  "adapter_version": string;
  "completed_unit_ids": Array<UUID>;
  "artifacts": Array<CheckpointUnitArtifacts>;
  "pending_unit_ids": Array<UUID>;
  "cursor": string;
};

export type DecimalString = string;

export type NonnegativeDecimalString = string;

export type CapabilityScope = {
  "languages": Array<string>;
  "source_types": Array<"epub" | "pdf_text" | "pdf_scanned" | "pdf_mixed">;
  "voice_version_ids": Array<UUID>;
  "model_revisions": Array<string>;
  "processing_config_sha256s": Array<SHA256>;
  "deliverable_kinds": Array<"audio" | "epub">;
};

export type MetricThreshold = {
  "metric": string;
  "unit": string;
  "direction": "upper" | "lower" | "equal";
  "value": DecimalString;
  "regression_tolerance": NonnegativeDecimalString;
};

export type DetectorBinding = {
  "id": UUID;
  "version": number;
  "engine": string;
  "engine_revision": string;
  "model_revision": string | null;
  "prompt_sha256": SHA256 | null;
  "input_modalities": Array<"text" | "image" | "audio" | "structure">;
  "risks": Array<"D01" | "D02" | "D03" | "D04" | "D05" | "D06">;
  "thresholds": Array<MetricThreshold>;
  "calibration_report_sha256": SHA256 | null;
};

export type VersionReference = {
  "id": UUID;
  "version": number;
};

export type RepairPresetReference = {
  "id": UUID;
  "version": number;
  "config_sha256": SHA256;
};

export type FeeLimits = {
  "currency": string;
  "per_production_minor": number;
  "daily_minor": number;
  "timezone": string;
};

export type BudgetRules = {
  "plan_steps": number;
  "replans": number;
  "reflections": number;
  "actions_per_turn": 1;
  "model_requests_per_finding": number;
  "tool_calls_per_finding": number;
  "tts_generations_per_block": number;
  "no_progress_repetitions": number;
  "request_timeout_seconds": number;
  "transient_retries": number;
  "fee_limits": FeeLimits | null;
};

export type QualityPolicyConfig = {
  "contract_version": 2;
  "canonicalization": "fv-json-v1";
  "applicability": CapabilityScope;
  "required_detectors": Array<DetectorBinding>;
  "adjudication_rule_sha256s": Array<SHA256>;
  "repair_presets": Array<RepairPresetReference>;
  "budget_rules": BudgetRules;
};

export type QualityPolicy = {
  "id": UUID;
  "version": number;
  "policy_hash": SHA256;
  "config": QualityPolicyConfig;
  "created_at": DateTime;
};

export type Qualification = {
  "id": UUID;
  "version": number;
  "revision": number;
  "contract_version": 2;
  "policy_hash": SHA256;
  "scope": CapabilityScope;
  "dataset_sha256": SHA256 | null;
  "report_sha256": SHA256 | null;
  "issuer_id": UUID | null;
  "issued_at": DateTime | null;
  "status": "draft" | "evaluating" | "active" | "suspended" | "revoked";
  "change_triggers": Array<"model" | "prompt" | "detector" | "threshold" | "encoder" | "structure" | "processing" | "voice" | "source">;
  "revocation_sequence": number;
  "created_at": DateTime;
};

export type TestedVersions = {
  "platform": string;
  "os_version": string;
  "reader": string;
  "reader_version": string;
  "encoder_version": string;
  "packager_version": string;
};

export type CompatibilityLimits = {
  "chapters": number;
  "sentences": number;
  "duration_samples": number;
  "sample_rate": number;
  "size_bytes": number;
};

export type DeviceTestReference = {
  "artifact_sha256": SHA256;
  "evidence_id": UUID;
};

export type CompatibilityProfile = {
  "id": UUID;
  "version": number;
  "contract_version": 2;
  "deliverable_kind": "audio" | "epub";
  "tested_versions": Array<TestedVersions>;
  "file_features": Array<string>;
  "limits": CompatibilityLimits;
  "device_tests": Array<DeviceTestReference>;
  "status": "draft" | "active" | "suspended" | "revoked";
  "created_at": DateTime;
};

export type GateEvidence = {
  "Q1": Array<UUID>;
  "Q2": Array<UUID>;
  "Q3": Array<UUID>;
  "Q4": Array<UUID>;
  "Q5": Array<UUID>;
};

export type QualificationReference = {
  "id": UUID;
  "version": number;
  "policy_hash": SHA256;
  "revocation_sequence": number;
};

export type ReleaseBlocker = {
  "code": string;
  "detail": string;
};

export type ReleaseDecision = {
  "id": UUID;
  "contract_version": 2;
  "request_id": UUID;
  "export_id": UUID;
  "deliverable_kind": "audio" | "epub";
  "artifact_id": UUID;
  "artifact_sha256": SHA256;
  "production_id": UUID;
  "production_snapshot_sha256": SHA256;
  "quality_revision": number;
  "quality_snapshot_sha256": SHA256;
  "gate_evidence": GateEvidence;
  "qualification": QualificationReference | null;
  "compatibility_profile": VersionReference | null;
  "decision": "released" | "blocked";
  "blockers": Array<ReleaseBlocker>;
  "created_at": DateTime;
};

export type WorkerHealth = {
  "worker_id": UUID;
  "online": boolean;
  "ready_capabilities": Array<string>;
};

export type HealthReady = {
  "ready": boolean;
  "database": "ready" | "error";
  "migration": "ready" | "error";
  "disk": "ready" | "low" | "error";
  "workers": Array<WorkerHealth>;
};

export type ProblemDetails = {
  "type": string;
  "title": string;
  "status": number;
  "detail": string;
  "instance": string;
  "code": string;
  "request_id": UUID;
  "retryable": boolean;
  "affected_scope": Array<UUID>;
  "blockers"?: Array<ReleaseBlocker>;
  "health"?: HealthReady;
};

export type RequestCommand = {
  "request_id": UUID;
};

export type CreateSession = {
  "request_id": UUID;
  "pairing_code": string;
};

export type SessionRecord = {
  "principal_id": UUID;
  "role": "user" | "maintainer";
  "expires_at": DateTime;
  "csrf_token": string;
};

export type SessionClosed = {
  "closed": true;
};

export type CreateUpload = {
  "request_id": UUID;
  "size_bytes": number;
  "sha256": SHA256;
  "media_type": string;
  "purpose": "source" | "voice" | "task_output" | "checkpoint" | "evidence" | "text_revision" | "configuration";
  "task_id": UUID | null;
};

export type UploadChunk = {
  "index": number;
  "size_bytes": number;
  "sha256": SHA256;
};

export type UploadRecord = {
  "id": UUID;
  "size_bytes": number;
  "sha256": SHA256;
  "chunk_size_bytes": number;
  "expires_at": DateTime;
  "received_chunks": Array<UploadChunk>;
  "state": "open" | "completed" | "expired";
  "artifact": ArtifactReference | null;
};

export type ChunkAccepted = {
  "upload_id": UUID;
  "index": number;
  "size_bytes": number;
  "sha256": SHA256;
};

export type ArtifactRecord = {
  "id": UUID;
  "size_bytes": number;
  "sha256": SHA256;
  "media_type": string;
  "validation_status": "validated" | "invalid" | "pending";
  "created_at": DateTime;
};

export type BookRecord = {
  "id": UUID;
  "title": string;
  "authors": Array<string>;
  "revision": number;
  "created_at": DateTime;
};

export type CreateBook = {
  "request_id": UUID;
  "title": string;
  "authors": Array<string>;
};

export type SourceSelection = {
  "artifact_id": UUID;
  "role": "primary" | "reference";
  "format": "epub" | "pdf_text" | "pdf_scanned" | "pdf_mixed";
  "edition": string;
};

export type CreateImport = {
  "request_id": UUID;
  "sources": Array<SourceSelection>;
  "selected_primary_artifact_id": UUID;
};

export type TaskAccepted = {
  "task_id": UUID;
  "status_url": string;
};

export type CreateTextRevision = {
  "request_id": UUID;
  "parent_revision_id": UUID;
  "structure_artifact_id": UUID;
  "structure_sha256": SHA256;
};

export type TextRevisionRecord = {
  "id": UUID;
  "book_id": UUID;
  "revision": number;
  "parent_revision_id": UUID | null;
  "structure_artifact_id": UUID;
  "structure_sha256": SHA256;
  "created_at": DateTime;
};

export type RevisionList = {
  "book_id": UUID;
  "resource_revision": number;
  "items": Array<TextRevisionRecord>;
};

export type CreateVoice = {
  "request_id": UUID;
  "name": string;
};

export type VoiceRecord = {
  "id": UUID;
  "name": string;
  "revision": number;
  "created_at": DateTime;
};

export type CreateVoiceVersion = {
  "request_id": UUID;
  "reference_artifact_id": UUID;
  "reference_text": string;
  "compatible_model_revisions": Array<string>;
  "config_sha256": SHA256;
};

export type VoiceVersionRecord = {
  "id": UUID;
  "voice_id": UUID;
  "version": number;
  "reference_artifact_id": UUID;
  "reference_text": string;
  "compatible_model_revisions": Array<string>;
  "config_sha256": SHA256;
  "approved_review_id": UUID | null;
  "created_at": DateTime;
};

export type TaskState = "queued" | "running" | "pause_requested" | "paused" | "completed" | "failed" | "cancelled";

export type ProductionControlState = "active" | "pausing" | "paused" | "cancelled";

export type ExecutionState = "queued" | "running" | "blocked" | "failed" | "completed";

export type TaskRecord = {
  "id": UUID;
  "production_id": UUID;
  "stage": string;
  "state": TaskState;
  "revision": number;
  "attempt_no": number;
  "input_snapshot_sha256": SHA256;
  "output_artifacts": Array<ArtifactReference>;
  "last_error": ProblemDetails | null;
  "created_at": DateTime;
};

export type TaskControlCommand = {
  "request_id": UUID;
  "expected_task_revision": number;
};

export type ProductionRecord = {
  "id": UUID;
  "book_id": UUID;
  "text_revision_id": UUID;
  "voice_version_id": UUID;
  "model_revision": string;
  "config_sha256": SHA256;
  "snapshot_sha256": SHA256;
  "scope": Array<UUID>;
  "control_state": ProductionControlState;
  "control_revision": number;
  "execution_state": ExecutionState;
  "quality_revision": number;
  "created_at": DateTime;
};

export type WorkerRegistration = {
  "request_id": UUID;
  "protocol_version": 1;
  "name": string;
  "platform": "container" | "macos";
  "capabilities": Array<string>;
  "model_revisions": Array<string>;
};

export type WorkerRecord = {
  "id": UUID;
  "protocol_version": 1;
  "name": string;
  "platform": "container" | "macos";
  "capabilities": Array<string>;
  "model_revisions": Array<string>;
  "online": boolean;
  "registered_at": DateTime;
};

export type ClaimTasks = {
  "request_id": UUID;
  "capabilities": Array<string>;
  "model_revisions": Array<string>;
};

export type HeartbeatAccepted = {
  "task_id": UUID;
  "attempt_no": number;
  "expires_at": DateTime;
  "app_generation": UUID;
  "control_state": ProductionControlState;
  "control_revision": number;
};

export type SubmissionReceipt = {
  "receipt_id": UUID;
  "request_id": UUID;
  "task_id": UUID;
  "attempt_no": number;
  "accepted_at": DateTime;
};

export type CreateReview = {
  "request_id": UUID;
  "artifact_id": UUID;
  "artifact_sha256": SHA256;
  "scope_id": UUID;
  "dimension": string;
  "conclusion": "approved" | "rejected" | "uncertain";
  "voice_version_id": UUID | null;
  "comment": string;
};

export type ReviewRecord = {
  "id": UUID;
  "artifact_id": UUID;
  "artifact_sha256": SHA256;
  "scope_id": UUID;
  "dimension": string;
  "conclusion": "approved" | "rejected" | "uncertain";
  "voice_version_id": UUID | null;
  "actor_id": UUID;
  "comment": string;
  "created_at": DateTime;
};

export type GateStatus = {
  "gate": "Q1" | "Q2" | "Q3" | "Q4" | "Q5";
  "status": "pending" | "pass" | "blocked";
  "evidence_ids": Array<UUID>;
  "blockers": Array<ReleaseBlocker>;
};

export type QualitySnapshot = {
  "production_id": UUID;
  "snapshot_sha256": SHA256;
  "revision": number;
  "contract_version": 2;
  "policy_hash": SHA256 | null;
  "gates": Array<GateStatus>;
  "qualification": QualificationReference | null;
  "compatibility_profile": VersionReference | null;
  "blockers": Array<ReleaseBlocker>;
};

export type CreateExport = {
  "request_id": UUID;
  "production_id": UUID;
  "candidate_kind": "preview" | "formal_candidate";
  "deliverable_kind": "audio" | "epub";
  "scope": Array<UUID>;
};

export type ExportAccepted = {
  "export_id": UUID;
  "task_id": UUID;
  "status_url": string;
};

export type ResumeManifest = {
  "production": ProductionRecord;
  "source_sha256s": Array<SHA256>;
  "completed_unit_ids": Array<UUID>;
  "pending_unit_ids": Array<UUID>;
  "artifacts": Array<CheckpointUnitArtifacts>;
  "failed_task_ids": Array<UUID>;
  "unresolved_issue_ids": Array<UUID>;
  "workers": Array<WorkerHealth>;
  "last_event_sequence": number;
  "next_step": string;
  "recovery_command": string | null;
  "updated_at": DateTime;
};

export type HealthLive = {
  "status": "alive";
};

export type CreateAgentRun = {
  "request_id": UUID;
  "production_snapshot_sha256": SHA256;
  "scope": Array<UUID>;
  "policy_hash": SHA256;
  "provider_id": string;
  "model_revision": string;
  "template_version": string;
  "schema_version": string;
  "external_authorization_id": UUID;
};

export type BudgetUsage = {
  "currency": string;
  "reserved_minor": number;
  "actual_minor": number;
  "unknown_minor": number;
  "model_requests": number;
  "tool_calls": number;
};

export type AgentRunState = "queued" | "running" | "waiting_tool" | "waiting_provider" | "budget_exhausted" | "needs_input" | "cancelled" | "no_progress" | "stale" | "needs_maintenance" | "completed";

export type AgentRunAccepted = {
  "run_id": UUID;
  "status_url": string;
};

export type AgentRunRecord = {
  "id": UUID;
  "production_id": UUID;
  "snapshot_sha256": SHA256;
  "provider_id": string;
  "model_revision": string;
  "template_version": string;
  "schema_version": string;
  "state": AgentRunState;
  "budget": BudgetUsage;
  "proposal_ids": Array<UUID>;
  "last_step_sequence": number;
  "created_at": DateTime;
};

export type ApplyRepairProposal = {
  "request_id": UUID;
  "expected_quality_revision": number;
  "production_snapshot_sha256": SHA256;
};

export type RepairApplied = {
  "proposal_id": UUID;
  "task_ids": Array<UUID>;
  "invalidated_node_ids": Array<UUID>;
  "retained_node_ids": Array<UUID>;
};

export type QualifyPolicy = {
  "request_id": UUID;
  "policy_version": number;
  "policy_hash": SHA256;
  "qualification_id": UUID;
  "qualification_version": number;
  "scope": CapabilityScope;
  "dataset_sha256": SHA256;
  "report_sha256": SHA256;
  "change_triggers": Array<"model" | "prompt" | "detector" | "threshold" | "encoder" | "structure" | "processing" | "voice" | "source">;
};

export type RevokeQualification = {
  "request_id": UUID;
  "qualification_version": number;
  "expected_revocation_sequence": number;
  "reason": string;
};

export type RevocationReceipt = {
  "qualification_id": UUID;
  "qualification_version": number;
  "revocation_sequence": number;
  "affected_release_ids": Array<UUID>;
};

export type DownloadReference = {
  "artifact_id": UUID;
  "sha256": SHA256;
  "size_bytes": number;
  "download_url": string;
};

export type ReleaseResponse = {
  "decision": ReleaseDecision;
  "download": DownloadReference;
};

export type DeviceEnvironment = {
  "platform": string;
  "os_version": string;
  "reader": string;
  "reader_version": string;
};

export type IssueLocation = {
  "export_id": UUID;
  "artifact_sha256": SHA256;
  "chapter_id": UUID | null;
  "sentence_id": UUID | null;
  "start_sample": number | null;
  "end_sample": number | null;
  "sample_rate": number | null;
  "environment": DeviceEnvironment | null;
};

export type IssueState = "awaiting_location" | "triaged" | "planned" | "candidate" | "awaiting_device_evidence" | "resolved_system" | "awaiting_feedback" | "closed_confirmed" | "reopened" | "withdrawn";

export type CreateIssue = {
  "request_id": UUID;
  "book_id": UUID;
  "description": string;
  "location": IssueLocation | null;
  "attachment_ids": Array<UUID>;
};

export type IssueRecord = {
  "id": UUID;
  "book_id": UUID;
  "description": string;
  "status": IssueState;
  "severity": "P0" | "P1" | "P2" | "P3";
  "revision": number;
  "location": IssueLocation | null;
  "created_at": DateTime;
};

export type LocateIssue = {
  "request_id": UUID;
  "location": IssueLocation;
  "evidence_ids": Array<UUID>;
};

export type CreateRepairPlan = {
  "request_id": UUID;
  "base_export_id": UUID;
  "base_artifact_sha256": SHA256;
  "target_production_id": UUID;
  "changed_node_ids": Array<UUID>;
  "expected_quality_revision": number;
};

export type RepairPlanRecord = {
  "id": UUID;
  "version": number;
  "issue_id": UUID;
  "issue_revision": number;
  "base_export_id": UUID;
  "base_artifact_sha256": SHA256;
  "target_production_id": UUID;
  "changed_node_ids": Array<UUID>;
  "invalidated_node_ids": Array<UUID>;
  "retained_node_ids": Array<UUID>;
  "retest_cases": Array<string>;
  "rollback_artifact_ids": Array<UUID>;
  "required_device_environment": DeviceEnvironment | null;
  "created_at": DateTime;
};

export type AppendIssueEvidence = {
  "request_id": UUID;
  "issue_revision": number;
  "plan_id": UUID;
  "plan_version": number;
  "candidate_artifact_id": UUID;
  "candidate_sha256": SHA256;
  "contract_version": 2;
  "scope_id": UUID;
  "gate": "Q1" | "Q2" | "Q3" | "Q4" | "Q5";
  "case_id": string;
  "rule_version": string;
  "outcome": "pass" | "suspect" | "fail" | "unknown" | "error";
  "evidence_kind": "tool" | "human" | "device_test" | "compatibility_match";
  "environment": DeviceEnvironment | null;
  "attachment_ids": Array<UUID>;
};

export type EvidenceAppended = {
  "evidence_id": UUID;
  "server_sequence": number;
  "issue_revision": number;
};

export type ResolutionRecord = {
  "id": UUID;
  "issue_id": UUID;
  "issue_revision": number;
  "plan_id": UUID;
  "plan_version": number;
  "candidate_sha256": SHA256;
  "proof_id": UUID;
  "reproduction_evidence_id": UUID;
  "evidence_ids": Array<UUID>;
  "resolution_kind": "resolved_system" | "awaiting_feedback";
  "user_confirmation_id": UUID | null;
  "created_at": DateTime;
};

export type ConfirmIssue = {
  "request_id": UUID;
  "resolution_id": UUID;
  "feedback": string;
};

export type ReopenIssue = {
  "request_id": UUID;
  "reproduction_description": string;
  "evidence_ids": Array<UUID>;
};
