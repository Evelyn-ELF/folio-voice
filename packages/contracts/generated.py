"""自动生成，请勿手改；运行约束、条件与权限须另按源Schema及服务规则验证。"""

from typing import Literal, NotRequired, TypedDict

SCHEMA_SHA256 = "ae5453e3fb698de9c8659051fc515f784d091525cd95bc964f3af38469b6954b"

type UUID = str

type SHA256 = str

class Action(TypedDict):
    tool: Literal['get_evidence', 'inspect_source', 'compare_stages', 'run_detector', 'submit_repair']
    resource_ids: list[UUID]
    binding_id: UUID | None

class PlanStep(TypedDict):
    step_id: int
    goal: str
    expected_evidence: str

class AgentDecision(TypedDict):
    run_id: UUID
    snapshot_hash: SHA256
    plan_revision: int
    decision: Literal['observe', 'propose_repair', 'stop']
    reason_summary: str
    evidence_ids: list[UUID]
    plan_steps: list[PlanStep]
    action: Action | None
    stop_reason: Literal['complete', 'no_progress', 'budget_exhausted', 'needs_input', 'needs_maintenance', 'stale', 'cancelled'] | None

class Interval(TypedDict):
    start_sample: int
    end_sample: int

class Evidence(TypedDict):
    id: UUID
    contract_version: Literal[2]
    snapshot_hash: SHA256
    artifact_sha256: SHA256
    binding_id: UUID
    scope_id: UUID
    risk: Literal['D01', 'D02', 'D03', 'D04', 'D05', 'D06']
    outcome: Literal['pass', 'suspect', 'fail', 'unknown', 'error']
    intervals: list[Interval]
    attachment_ids: list[UUID]
    server_sequence: int

class ResolveCommand(TypedDict):
    request_id: UUID
    issue_id: UUID
    issue_revision: int
    candidate_sha256: SHA256
    proof_id: UUID
    quality_revision: int
    contract_version: Literal[2]

class ReleaseCommand(TypedDict):
    request_id: UUID
    artifact_id: UUID
    artifact_sha256: SHA256
    deliverable_kind: Literal['audio', 'epub']
    quality_revision: int
    contract_version: Literal[2]

class CandidateSelection(TypedDict):
    baseline_sha256: SHA256
    candidate_sha256: SHA256
    policy_sha256: SHA256
    target_finding_ids: list[UUID]
    comparison_evidence_ids: list[UUID]
    decision: Literal['provisional', 'final', 'reject']
    reason_codes: list[Literal['target_unresolved', 'new_defect', 'regression', 'missing_evidence', 'scope_mismatch', 'all_checks_passed', 'lower_rebuild_cost']]

type DateTime = str

class ArtifactReference(TypedDict):
    artifact_id: UUID
    size_bytes: int
    sha256: SHA256

class CreateProduction(TypedDict):
    book_id: UUID
    text_revision_id: UUID
    voice_version_id: UUID
    model_revision: str
    config_sha256: SHA256
    scope: list[UUID]
    request_id: UUID

class ProductionAccepted(TypedDict):
    production_id: UUID
    control_revision: int
    status_url: str

class TaskLease(TypedDict):
    task_id: UUID
    production_id: UUID
    attempt_no: int
    lease_token: str
    input_snapshot_sha256: SHA256
    app_generation: UUID
    expires_at: DateTime
    control_revision: int
    input_artifacts: list[ArtifactReference]

class Heartbeat(TypedDict):
    attempt_no: int
    lease_token: str
    input_snapshot_sha256: SHA256
    app_generation: UUID

class CheckpointCommand(TypedDict):
    request_id: UUID
    attempt_no: int
    lease_token: str
    input_snapshot_sha256: SHA256
    app_generation: UUID
    checkpoint_artifact_id: UUID
    completed_unit_ids: list[UUID]

class TaskResult(TypedDict):
    request_id: UUID
    attempt_no: int
    lease_token: str
    input_snapshot_sha256: SHA256
    app_generation: UUID
    output_artifact_ids: list[UUID]
    result_summary: str

class ProductionControl(TypedDict):
    request_id: UUID
    expected_control_revision: int

class CheckpointUnitArtifacts(TypedDict):
    unit_id: UUID
    artifacts: list[ArtifactReference]

class CheckpointManifest(TypedDict):
    input_snapshot_sha256: SHA256
    adapter_version: str
    completed_unit_ids: list[UUID]
    artifacts: list[CheckpointUnitArtifacts]
    pending_unit_ids: list[UUID]
    cursor: str

type DecimalString = str

type NonnegativeDecimalString = str

class CapabilityScope(TypedDict):
    languages: list[str]
    source_types: list[Literal['epub', 'pdf_text', 'pdf_scanned', 'pdf_mixed']]
    voice_version_ids: list[UUID]
    model_revisions: list[str]
    processing_config_sha256s: list[SHA256]
    deliverable_kinds: list[Literal['audio', 'epub']]

class MetricThreshold(TypedDict):
    metric: str
    unit: str
    direction: Literal['upper', 'lower', 'equal']
    value: DecimalString
    regression_tolerance: NonnegativeDecimalString

class DetectorBinding(TypedDict):
    id: UUID
    version: int
    engine: str
    engine_revision: str
    model_revision: str | None
    prompt_sha256: SHA256 | None
    input_modalities: list[Literal['text', 'image', 'audio', 'structure']]
    risks: list[Literal['D01', 'D02', 'D03', 'D04', 'D05', 'D06']]
    thresholds: list[MetricThreshold]
    calibration_report_sha256: SHA256 | None

class VersionReference(TypedDict):
    id: UUID
    version: int

class RepairPresetReference(TypedDict):
    id: UUID
    version: int
    config_sha256: SHA256

class FeeLimits(TypedDict):
    currency: str
    per_production_minor: int
    daily_minor: int
    timezone: str

class BudgetRules(TypedDict):
    plan_steps: int
    replans: int
    reflections: int
    actions_per_turn: Literal[1]
    model_requests_per_finding: int
    tool_calls_per_finding: int
    tts_generations_per_block: int
    no_progress_repetitions: int
    request_timeout_seconds: int
    transient_retries: int
    fee_limits: FeeLimits | None

class QualityPolicyConfig(TypedDict):
    contract_version: Literal[2]
    canonicalization: Literal['fv-json-v1']
    applicability: CapabilityScope
    required_detectors: list[DetectorBinding]
    adjudication_rule_sha256s: list[SHA256]
    repair_presets: list[RepairPresetReference]
    budget_rules: BudgetRules

class QualityPolicy(TypedDict):
    id: UUID
    version: int
    policy_hash: SHA256
    config: QualityPolicyConfig
    created_at: DateTime

class Qualification(TypedDict):
    id: UUID
    version: int
    revision: int
    contract_version: Literal[2]
    policy_hash: SHA256
    scope: CapabilityScope
    dataset_sha256: SHA256 | None
    report_sha256: SHA256 | None
    issuer_id: UUID | None
    issued_at: DateTime | None
    status: Literal['draft', 'evaluating', 'active', 'suspended', 'revoked']
    change_triggers: list[Literal['model', 'prompt', 'detector', 'threshold', 'encoder', 'structure', 'processing', 'voice', 'source']]
    revocation_sequence: int
    created_at: DateTime

class TestedVersions(TypedDict):
    platform: str
    os_version: str
    reader: str
    reader_version: str
    encoder_version: str
    packager_version: str

class CompatibilityLimits(TypedDict):
    chapters: int
    sentences: int
    duration_samples: int
    sample_rate: int
    size_bytes: int

class DeviceTestReference(TypedDict):
    artifact_sha256: SHA256
    evidence_id: UUID

class CompatibilityProfile(TypedDict):
    id: UUID
    version: int
    contract_version: Literal[2]
    deliverable_kind: Literal['audio', 'epub']
    tested_versions: list[TestedVersions]
    file_features: list[str]
    limits: CompatibilityLimits
    device_tests: list[DeviceTestReference]
    status: Literal['draft', 'active', 'suspended', 'revoked']
    created_at: DateTime

class GateEvidence(TypedDict):
    Q1: list[UUID]
    Q2: list[UUID]
    Q3: list[UUID]
    Q4: list[UUID]
    Q5: list[UUID]

class QualificationReference(TypedDict):
    id: UUID
    version: int
    policy_hash: SHA256
    revocation_sequence: int

class ReleaseBlocker(TypedDict):
    code: str
    detail: str

class ReleaseDecision(TypedDict):
    id: UUID
    contract_version: Literal[2]
    request_id: UUID
    export_id: UUID
    deliverable_kind: Literal['audio', 'epub']
    artifact_id: UUID
    artifact_sha256: SHA256
    production_id: UUID
    production_snapshot_sha256: SHA256
    quality_revision: int
    quality_snapshot_sha256: SHA256
    gate_evidence: GateEvidence
    qualification: QualificationReference | None
    compatibility_profile: VersionReference | None
    decision: Literal['released', 'blocked']
    blockers: list[ReleaseBlocker]
    created_at: DateTime

class WorkerHealth(TypedDict):
    worker_id: UUID
    online: bool
    ready_capabilities: list[str]

class HealthReady(TypedDict):
    ready: bool
    database: Literal['ready', 'error']
    migration: Literal['ready', 'error']
    disk: Literal['ready', 'low', 'error']
    workers: list[WorkerHealth]

class ProblemDetails(TypedDict):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: UUID
    retryable: bool
    affected_scope: list[UUID]
    blockers: NotRequired[list[ReleaseBlocker]]
    health: NotRequired[HealthReady]

class RequestCommand(TypedDict):
    request_id: UUID

class CreateSession(TypedDict):
    request_id: UUID
    pairing_code: str

class SessionRecord(TypedDict):
    principal_id: UUID
    role: Literal['user', 'maintainer']
    expires_at: DateTime
    csrf_token: str

class SessionClosed(TypedDict):
    closed: Literal[True]

class CreateUpload(TypedDict):
    request_id: UUID
    size_bytes: int
    sha256: SHA256
    media_type: str
    purpose: Literal['source', 'voice', 'task_output', 'checkpoint', 'evidence', 'text_revision', 'configuration']
    task_id: UUID | None

class UploadChunk(TypedDict):
    index: int
    size_bytes: int
    sha256: SHA256

class UploadRecord(TypedDict):
    id: UUID
    size_bytes: int
    sha256: SHA256
    chunk_size_bytes: int
    expires_at: DateTime
    received_chunks: list[UploadChunk]
    state: Literal['open', 'completed', 'expired']
    artifact: ArtifactReference | None

class ChunkAccepted(TypedDict):
    upload_id: UUID
    index: int
    size_bytes: int
    sha256: SHA256

class ArtifactRecord(TypedDict):
    id: UUID
    size_bytes: int
    sha256: SHA256
    media_type: str
    validation_status: Literal['validated', 'invalid', 'pending']
    created_at: DateTime

class BookRecord(TypedDict):
    id: UUID
    title: str
    authors: list[str]
    revision: int
    created_at: DateTime

class CreateBook(TypedDict):
    request_id: UUID
    title: str
    authors: list[str]

class SourceSelection(TypedDict):
    artifact_id: UUID
    role: Literal['primary', 'reference']
    format: Literal['epub', 'pdf_text', 'pdf_scanned', 'pdf_mixed']
    edition: str

class CreateImport(TypedDict):
    request_id: UUID
    sources: list[SourceSelection]
    selected_primary_artifact_id: UUID

class TaskAccepted(TypedDict):
    task_id: UUID
    status_url: str

class CreateTextRevision(TypedDict):
    request_id: UUID
    parent_revision_id: UUID
    structure_artifact_id: UUID
    structure_sha256: SHA256

class TextRevisionRecord(TypedDict):
    id: UUID
    book_id: UUID
    revision: int
    parent_revision_id: UUID | None
    structure_artifact_id: UUID
    structure_sha256: SHA256
    created_at: DateTime

class RevisionList(TypedDict):
    book_id: UUID
    resource_revision: int
    items: list[TextRevisionRecord]

class CreateVoice(TypedDict):
    request_id: UUID
    name: str

class VoiceRecord(TypedDict):
    id: UUID
    name: str
    revision: int
    created_at: DateTime

class CreateVoiceVersion(TypedDict):
    request_id: UUID
    reference_artifact_id: UUID
    reference_text: str
    compatible_model_revisions: list[str]
    config_sha256: SHA256

class VoiceVersionRecord(TypedDict):
    id: UUID
    voice_id: UUID
    version: int
    reference_artifact_id: UUID
    reference_text: str
    compatible_model_revisions: list[str]
    config_sha256: SHA256
    approved_review_id: UUID | None
    created_at: DateTime

type TaskState = Literal['queued', 'running', 'pause_requested', 'paused', 'completed', 'failed', 'cancelled']

type ProductionControlState = Literal['active', 'pausing', 'paused', 'cancelled']

type ExecutionState = Literal['queued', 'running', 'blocked', 'failed', 'completed']

class TaskRecord(TypedDict):
    id: UUID
    production_id: UUID
    stage: str
    state: TaskState
    revision: int
    attempt_no: int
    input_snapshot_sha256: SHA256
    output_artifacts: list[ArtifactReference]
    last_error: ProblemDetails | None
    created_at: DateTime

class TaskControlCommand(TypedDict):
    request_id: UUID
    expected_task_revision: int

class ProductionRecord(TypedDict):
    id: UUID
    book_id: UUID
    text_revision_id: UUID
    voice_version_id: UUID
    model_revision: str
    config_sha256: SHA256
    snapshot_sha256: SHA256
    scope: list[UUID]
    control_state: ProductionControlState
    control_revision: int
    execution_state: ExecutionState
    quality_revision: int
    created_at: DateTime

class WorkerRegistration(TypedDict):
    request_id: UUID
    protocol_version: Literal[1]
    name: str
    platform: Literal['container', 'macos']
    capabilities: list[str]
    model_revisions: list[str]

class WorkerRecord(TypedDict):
    id: UUID
    protocol_version: Literal[1]
    name: str
    platform: Literal['container', 'macos']
    capabilities: list[str]
    model_revisions: list[str]
    online: bool
    registered_at: DateTime

class ClaimTasks(TypedDict):
    request_id: UUID
    capabilities: list[str]
    model_revisions: list[str]

class HeartbeatAccepted(TypedDict):
    task_id: UUID
    attempt_no: int
    expires_at: DateTime
    app_generation: UUID
    control_state: ProductionControlState
    control_revision: int

class SubmissionReceipt(TypedDict):
    receipt_id: UUID
    request_id: UUID
    task_id: UUID
    attempt_no: int
    accepted_at: DateTime

class CreateReview(TypedDict):
    request_id: UUID
    artifact_id: UUID
    artifact_sha256: SHA256
    scope_id: UUID
    dimension: str
    conclusion: Literal['approved', 'rejected', 'uncertain']
    voice_version_id: UUID | None
    comment: str

class ReviewRecord(TypedDict):
    id: UUID
    artifact_id: UUID
    artifact_sha256: SHA256
    scope_id: UUID
    dimension: str
    conclusion: Literal['approved', 'rejected', 'uncertain']
    voice_version_id: UUID | None
    actor_id: UUID
    comment: str
    created_at: DateTime

class GateStatus(TypedDict):
    gate: Literal['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    status: Literal['pending', 'pass', 'blocked']
    evidence_ids: list[UUID]
    blockers: list[ReleaseBlocker]

class QualitySnapshot(TypedDict):
    production_id: UUID
    snapshot_sha256: SHA256
    revision: int
    contract_version: Literal[2]
    policy_hash: SHA256 | None
    gates: list[GateStatus]
    qualification: QualificationReference | None
    compatibility_profile: VersionReference | None
    blockers: list[ReleaseBlocker]

class CreateExport(TypedDict):
    request_id: UUID
    production_id: UUID
    candidate_kind: Literal['preview', 'formal_candidate']
    deliverable_kind: Literal['audio', 'epub']
    scope: list[UUID]

class ExportAccepted(TypedDict):
    export_id: UUID
    task_id: UUID
    status_url: str

class ResumeManifest(TypedDict):
    production: ProductionRecord
    source_sha256s: list[SHA256]
    completed_unit_ids: list[UUID]
    pending_unit_ids: list[UUID]
    artifacts: list[CheckpointUnitArtifacts]
    failed_task_ids: list[UUID]
    unresolved_issue_ids: list[UUID]
    workers: list[WorkerHealth]
    last_event_sequence: int
    next_step: str
    recovery_command: str | None
    updated_at: DateTime

class HealthLive(TypedDict):
    status: Literal['alive']

class CreateAgentRun(TypedDict):
    request_id: UUID
    production_snapshot_sha256: SHA256
    scope: list[UUID]
    policy_hash: SHA256
    provider_id: str
    model_revision: str
    template_version: str
    schema_version: str
    external_authorization_id: UUID

class BudgetUsage(TypedDict):
    currency: str
    reserved_minor: int
    actual_minor: int
    unknown_minor: int
    model_requests: int
    tool_calls: int

type AgentRunState = Literal['queued', 'running', 'waiting_tool', 'waiting_provider', 'budget_exhausted', 'needs_input', 'cancelled', 'no_progress', 'stale', 'needs_maintenance', 'completed']

class AgentRunAccepted(TypedDict):
    run_id: UUID
    status_url: str

class AgentRunRecord(TypedDict):
    id: UUID
    production_id: UUID
    snapshot_sha256: SHA256
    provider_id: str
    model_revision: str
    template_version: str
    schema_version: str
    state: AgentRunState
    budget: BudgetUsage
    proposal_ids: list[UUID]
    last_step_sequence: int
    created_at: DateTime

class ApplyRepairProposal(TypedDict):
    request_id: UUID
    expected_quality_revision: int
    production_snapshot_sha256: SHA256

class RepairApplied(TypedDict):
    proposal_id: UUID
    task_ids: list[UUID]
    invalidated_node_ids: list[UUID]
    retained_node_ids: list[UUID]

class QualifyPolicy(TypedDict):
    request_id: UUID
    policy_version: int
    policy_hash: SHA256
    qualification_id: UUID
    qualification_version: int
    scope: CapabilityScope
    dataset_sha256: SHA256
    report_sha256: SHA256
    change_triggers: list[Literal['model', 'prompt', 'detector', 'threshold', 'encoder', 'structure', 'processing', 'voice', 'source']]

class RevokeQualification(TypedDict):
    request_id: UUID
    qualification_version: int
    expected_revocation_sequence: int
    reason: str

class RevocationReceipt(TypedDict):
    qualification_id: UUID
    qualification_version: int
    revocation_sequence: int
    affected_release_ids: list[UUID]

class DownloadReference(TypedDict):
    artifact_id: UUID
    sha256: SHA256
    size_bytes: int
    download_url: str

class ReleaseResponse(TypedDict):
    decision: ReleaseDecision
    download: DownloadReference

class DeviceEnvironment(TypedDict):
    platform: str
    os_version: str
    reader: str
    reader_version: str

class IssueLocation(TypedDict):
    export_id: UUID
    artifact_sha256: SHA256
    chapter_id: UUID | None
    sentence_id: UUID | None
    start_sample: int | None
    end_sample: int | None
    sample_rate: int | None
    environment: DeviceEnvironment | None

type IssueState = Literal['awaiting_location', 'triaged', 'planned', 'candidate', 'awaiting_device_evidence', 'resolved_system', 'awaiting_feedback', 'closed_confirmed', 'reopened', 'withdrawn']

class CreateIssue(TypedDict):
    request_id: UUID
    book_id: UUID
    description: str
    location: IssueLocation | None
    attachment_ids: list[UUID]

class IssueRecord(TypedDict):
    id: UUID
    book_id: UUID
    description: str
    status: IssueState
    severity: Literal['P0', 'P1', 'P2', 'P3']
    revision: int
    location: IssueLocation | None
    created_at: DateTime

class LocateIssue(TypedDict):
    request_id: UUID
    location: IssueLocation
    evidence_ids: list[UUID]

class CreateRepairPlan(TypedDict):
    request_id: UUID
    base_export_id: UUID
    base_artifact_sha256: SHA256
    target_production_id: UUID
    changed_node_ids: list[UUID]
    expected_quality_revision: int

class RepairPlanRecord(TypedDict):
    id: UUID
    version: int
    issue_id: UUID
    issue_revision: int
    base_export_id: UUID
    base_artifact_sha256: SHA256
    target_production_id: UUID
    changed_node_ids: list[UUID]
    invalidated_node_ids: list[UUID]
    retained_node_ids: list[UUID]
    retest_cases: list[str]
    rollback_artifact_ids: list[UUID]
    required_device_environment: DeviceEnvironment | None
    created_at: DateTime

class AppendIssueEvidence(TypedDict):
    request_id: UUID
    issue_revision: int
    plan_id: UUID
    plan_version: int
    candidate_artifact_id: UUID
    candidate_sha256: SHA256
    contract_version: Literal[2]
    scope_id: UUID
    gate: Literal['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    case_id: str
    rule_version: str
    outcome: Literal['pass', 'suspect', 'fail', 'unknown', 'error']
    evidence_kind: Literal['tool', 'human', 'device_test', 'compatibility_match']
    environment: DeviceEnvironment | None
    attachment_ids: list[UUID]

class EvidenceAppended(TypedDict):
    evidence_id: UUID
    server_sequence: int
    issue_revision: int

class ResolutionRecord(TypedDict):
    id: UUID
    issue_id: UUID
    issue_revision: int
    plan_id: UUID
    plan_version: int
    candidate_sha256: SHA256
    proof_id: UUID
    reproduction_evidence_id: UUID
    evidence_ids: list[UUID]
    resolution_kind: Literal['resolved_system', 'awaiting_feedback']
    user_confirmation_id: UUID | None
    created_at: DateTime

class ConfirmIssue(TypedDict):
    request_id: UUID
    resolution_id: UUID
    feedback: str

class ReopenIssue(TypedDict):
    request_id: UUID
    reproduction_description: str
    evidence_ids: list[UUID]
