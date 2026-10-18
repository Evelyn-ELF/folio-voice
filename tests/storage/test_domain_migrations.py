"""内容/任务/质量迁移的真实SQLite约束；不代替HTTP或真实质量证据。"""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from packages.adapters.sqlite_migrations import connect, migrate
from packages.core.canonical import canonical_json, configuration_hash

ROOT = Path(__file__).resolve().parents[2]
TIME = "2026-10-18T00:00:00Z"
SHA = "a" * 64


def uid(value):
    return str(UUID(int=value))


class DomainMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "domain.sqlite")
        self.addCleanup(self.db.close)
        migrate(self.db)

    def insert(self, table, **values):
        return self.db.execute(
            f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",
            tuple(values.values()),
        )

    def seed(self):
        self.insert(
            "principals", id=uid(1), kind="human", role="maintainer", created_at=TIME
        )
        self.insert(
            "principals", id=uid(2), kind="worker", role="worker", created_at=TIME
        )
        self.insert(
            "artifacts",
            id=uid(3),
            sha256=SHA,
            size_bytes=100,
            media_type="application/json",
            validation_status="validated",
            created_at=TIME,
        )
        cfg = {"canonicalization": "fv-json-v1", "processing_version": 1}
        self.config_hash = configuration_hash(cfg)
        self.insert(
            "configurations",
            sha256=self.config_hash,
            config_json=canonical_json(cfg).decode(),
            created_at=TIME,
        )
        self.insert(
            "books",
            id=uid(4),
            title="自写测试书",
            authors_json='["测试作者"]',
            revision=1,
            created_at=TIME,
        )
        self.insert(
            "source_assets",
            id=uid(5),
            book_id=uid(4),
            artifact_id=uid(3),
            role="primary",
            format="epub",
            edition="自写",
            created_at=TIME,
        )
        self.insert(
            "text_revisions",
            id=uid(6),
            book_id=uid(4),
            revision=1,
            structure_artifact_id=uid(3),
            structure_sha256=SHA,
            created_at=TIME,
        )
        self.insert(
            "source_spans",
            id=uid(7),
            book_id=uid(4),
            text_revision_id=uid(6),
            source_asset_id=uid(5),
            locator="自写节点",
            start_offset=0,
            end_offset=10,
        )
        self.insert(
            "content_units",
            id=uid(8),
            text_revision_id=uid(6),
            position=0,
            kind="sentence",
            source_span_id=uid(7),
        )
        self.insert("voices", id=uid(9), name="自写声音", revision=1, created_at=TIME)
        self.insert(
            "voice_versions",
            id=uid(10),
            voice_id=uid(9),
            version=1,
            reference_artifact_id=uid(3),
            reference_text="自写参考文字",
            model_revisions_json='["自写模型@1"]',
            config_sha256=self.config_hash,
            created_at=TIME,
        )
        self.insert(
            "production_revisions",
            id=uid(11),
            book_id=uid(4),
            text_revision_id=uid(6),
            voice_version_id=uid(10),
            model_revision="自写模型@1",
            config_sha256=self.config_hash,
            snapshot_sha256=SHA,
            created_at=TIME,
        )
        self.insert(
            "production_scope",
            production_id=uid(11),
            text_revision_id=uid(6),
            unit_id=uid(8),
            position=0,
        )
        self.insert("scopes", id=uid(12), production_id=uid(11), snapshot_sha256=SHA)
        self.insert(
            "workers",
            id=uid(13),
            principal_id=uid(2),
            protocol_version=1,
            name="自写执行器",
            platform="container",
            capabilities_json='["parse_epub"]',
            model_revisions_json="[]",
            registered_at=TIME,
        )
        self.insert("app_generations", id=uid(14), started_at=TIME)
        self.insert(
            "tasks",
            id=uid(15),
            production_id=uid(11),
            stage="parse_epub",
            unit_key="自写单元",
            input_snapshot_sha256=SHA,
            state="queued",
            revision=1,
            created_at=TIME,
        )

    def attempt(self, number, token):
        self.insert(
            "attempts",
            task_id=uid(15),
            attempt_no=number,
            worker_id=uid(13),
            app_generation=uid(14),
            input_snapshot_sha256=SHA,
            state="running",
            created_at=TIME,
        )
        self.insert(
            "leases",
            id=uid(30 + number),
            task_id=uid(15),
            attempt_no=number,
            token_sha256=token * 64,
            expires_at="2026-10-18T00:02:00Z",
            created_at=TIME,
        )

    def test_all_entity_families_and_integrity(self):
        expected = {
            "principals",
            "auth_tokens",
            "browser_sessions",
            "pairing_codes",
            "artifacts",
            "artifact_owners",
            "artifact_dependencies",
            "uploads",
            "upload_chunks",
            "books",
            "source_assets",
            "text_revisions",
            "source_spans",
            "content_units",
            "text_mappings",
            "voices",
            "voice_versions",
            "production_revisions",
            "production_scope",
            "scopes",
            "scope_units",
            "workers",
            "app_generations",
            "tasks",
            "task_dependencies",
            "attempts",
            "leases",
            "task_inputs",
            "task_outputs",
            "result_receipts",
            "idempotency_receipts",
            "checkpoints",
            "checkpoint_units",
            "synthesis_blocks",
            "sentence_links",
            "review_records",
            "audit_events",
            "dependency_nodes",
            "dependency_edges",
            "detector_bindings",
            "quality_snapshots",
            "gate_results",
            "gate_evidence",
            "compatibility_profiles",
            "compatibility_device_tests",
            "findings",
            "finding_evidence",
            "issues",
            "issue_revisions",
            "repair_plans",
            "repair_plan_nodes",
            "repair_plan_rollbacks",
            "evidence_records",
            "evidence_intervals",
            "evidence_attachments",
            "repair_proofs",
            "proof_evidence",
            "resolution_records",
            "resolution_invalidations",
            "issue_applicability",
            "issue_confirmations",
            "exports",
            "export_artifacts",
            "release_decisions",
            "release_gate_evidence",
            "release_risk_events",
            "agent_runs",
            "agent_steps",
            "tool_receipts",
            "tool_receipt_artifacts",
            "repair_proposals",
            "budget_accounts",
            "production_budgets",
            "budget_ledger",
        }
        actual = {
            r[0]
            for r in self.db.execute(
                "SELECT name FROM sqlite_schema WHERE type='table'"
            )
        }
        self.assertTrue(expected <= actual, expected - actual)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_foreign_keys_version_ownership_and_ranges(self):
        self.seed()
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "production_scope",
                production_id=uid(11),
                text_revision_id=uid(99),
                unit_id=uid(8),
                position=1,
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "text_revisions",
                id=uid(16),
                book_id=uid(4),
                revision=1,
                structure_artifact_id=uid(3),
                structure_sha256=SHA,
                created_at=TIME,
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "source_spans",
                id=uid(16),
                book_id=uid(4),
                text_revision_id=uid(6),
                source_asset_id=uid(5),
                locator="错误范围",
                start_offset=9,
                end_offset=1,
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM artifacts WHERE id=?", (uid(3),))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE production_revisions SET snapshot_sha256=?", ("b" * 64,)
            )

    def test_lease_attempt_unique_and_cannot_reactivate(self):
        self.seed()
        self.attempt(1, "b")
        with self.assertRaises(sqlite3.IntegrityError):
            self.attempt(2, "c")
        self.db.execute(
            "UPDATE leases SET revoked_at=? WHERE task_id=?", (TIME, uid(15))
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE leases SET revoked_at=NULL WHERE task_id=?", (uid(15),)
            )
        self.insert(
            "leases",
            id=uid(32),
            task_id=uid(15),
            attempt_no=2,
            token_sha256="c" * 64,
            expires_at="2026-10-18T00:02:00Z",
            created_at=TIME,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "attempts",
                task_id=uid(15),
                attempt_no=1,
                worker_id=uid(13),
                app_generation=uid(14),
                input_snapshot_sha256=SHA,
                state="running",
                created_at=TIME,
            )

    def test_result_and_idempotency_receipts_are_unique_and_atomic(self):
        self.seed()
        self.attempt(1, "b")
        values = dict(
            id=uid(40),
            task_id=uid(15),
            attempt_no=1,
            principal_id=uid(2),
            request_id=uid(41),
            payload_sha256=SHA,
            result_summary="自写执行结果",
            accepted_at=TIME,
        )
        self.db.execute("BEGIN")
        self.insert("result_receipts", **values)
        self.db.execute(
            "UPDATE tasks SET state='completed',revision=2 WHERE id=?", (uid(15),)
        )
        self.db.execute("ROLLBACK")
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM result_receipts").fetchone()[0], 0
        )
        self.assertEqual(
            self.db.execute("SELECT state FROM tasks").fetchone()[0], "queued"
        )
        self.insert("result_receipts", **values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "result_receipts", **{**values, "id": uid(42), "request_id": uid(43)}
            )
        idem = dict(
            id=uid(44),
            principal_id=uid(2),
            operation="submit_result",
            request_id=uid(41),
            payload_sha256=SHA,
            response_status=200,
            response_json='{"结果":"已接收"}',
            created_at=TIME,
        )
        self.insert("idempotency_receipts", **idem)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "idempotency_receipts",
                **{**idem, "id": uid(45), "payload_sha256": "c" * 64},
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM result_receipts")

    def detector_and_evidence(self):
        binding = json.loads(
            (ROOT / "tests/fixtures/quality_records.json").read_text()
        )["QualityPolicy"]["config"]["required_detectors"][0]
        binding["id"] = uid(50)
        self.insert(
            "detector_bindings",
            id=uid(50),
            version=1,
            binding_sha256=configuration_hash(binding),
            descriptor_json=canonical_json(binding).decode(),
        )
        self.insert(
            "evidence_records",
            id=uid(51),
            production_id=uid(11),
            input_artifact_id=uid(3),
            artifact_sha256=SHA,
            binding_id=uid(50),
            scope_id=uid(12),
            risk="D04",
            outcome="unknown",
            evidence_kind="tool",
            actor_id=uid(2),
            gate="Q4",
            case_id="自写用例",
            rule_version="1",
            created_at=TIME,
        )

    def test_evidence_sequence_binding_attachments_and_history(self):
        self.seed()
        self.detector_and_evidence()
        first = self.db.execute(
            "SELECT server_sequence FROM evidence_records"
        ).fetchone()[0]
        self.insert(
            "evidence_records",
            id=uid(52),
            production_id=uid(11),
            input_artifact_id=uid(3),
            artifact_sha256=SHA,
            binding_id=uid(50),
            scope_id=uid(12),
            risk="D04",
            outcome="fail",
            evidence_kind="tool",
            actor_id=uid(2),
            gate="Q4",
            case_id="自写用例",
            rule_version="1",
            created_at=TIME,
        )
        self.assertGreater(
            self.db.execute(
                "SELECT max(server_sequence) FROM evidence_records"
            ).fetchone()[0],
            first,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "evidence_records",
                id=uid(53),
                production_id=uid(11),
                input_artifact_id=uid(3),
                artifact_sha256="b" * 64,
                binding_id=uid(50),
                scope_id=uid(12),
                risk="D04",
                outcome="pass",
                evidence_kind="tool",
                actor_id=uid(2),
                gate="Q4",
                case_id="自写用例",
                rule_version="1",
                created_at=TIME,
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE evidence_records SET outcome='pass'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "evidence_intervals",
                evidence_id=uid(51),
                start_sample=20,
                end_sample=10,
                sample_rate=48000,
            )
        self.insert("evidence_attachments", evidence_id=uid(51), artifact_id=uid(3))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM evidence_attachments")

    def test_checkpoint_and_review_cannot_cross_scope(self):
        self.seed()
        self.attempt(1, "b")
        self.insert(
            "content_units",
            id=uid(65),
            text_revision_id=uid(6),
            position=1,
            kind="sentence",
            source_span_id=uid(7),
        )
        self.insert(
            "checkpoints",
            id=uid(66),
            task_id=uid(15),
            attempt_no=1,
            production_id=uid(11),
            artifact_id=uid(3),
            input_snapshot_sha256=SHA,
            adapter_version="1",
            created_at=TIME,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "checkpoint_units",
                checkpoint_id=uid(66),
                production_id=uid(11),
                unit_id=uid(65),
                artifact_id=uid(3),
            )
        self.insert(
            "checkpoint_units",
            checkpoint_id=uid(66),
            production_id=uid(11),
            unit_id=uid(8),
            artifact_id=uid(3),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "review_records",
                id=uid(67),
                artifact_id=uid(3),
                artifact_sha256=SHA,
                scope_id=uid(12),
                dimension="自写试听",
                conclusion="approved",
                voice_version_id=uid(10),
                actor_id=uid(1),
                comment="非真实听审",
                created_at=TIME,
            )
        self.insert("scopes", id=uid(68), voice_version_id=uid(10), snapshot_sha256=SHA)
        self.insert(
            "review_records",
            id=uid(67),
            artifact_id=uid(3),
            artifact_sha256=SHA,
            scope_id=uid(68),
            dimension="自写试听",
            conclusion="approved",
            voice_version_id=uid(10),
            actor_id=uid(1),
            comment="非真实听审",
            created_at=TIME,
        )
        self.db.execute(
            "UPDATE voice_versions SET approved_review_id=? WHERE id=?",
            (uid(67), uid(10)),
        )

    def seed_delivery(self):
        self.seed()
        self.detector_and_evidence()
        policy = json.loads((ROOT / "tests/fixtures/quality_records.json").read_text())[
            "QualityPolicy"
        ]["config"]
        policy_hash = configuration_hash(policy)
        self.insert(
            "policy_configs",
            policy_hash=policy_hash,
            config_json=canonical_json(policy).decode(),
        )
        self.insert(
            "quality_policies",
            id=uid(90),
            version=1,
            policy_hash=policy_hash,
            created_at=TIME,
        )
        self.insert(
            "qualification_versions",
            id=uid(91),
            version=1,
            policy_hash=policy_hash,
            scope_json=canonical_json(policy["applicability"]).decode(),
            change_triggers_json='["detector"]',
            created_at=TIME,
        )
        for revision, status in ((1, "draft"), (2, "evaluating"), (3, "active")):
            self.insert(
                "qualification_events",
                event_id=uid(200 + revision),
                qualification_id=uid(91),
                qualification_version=1,
                revision=revision,
                status=status,
                revocation_sequence=0,
                dataset_sha256=SHA if revision == 3 else None,
                report_sha256=SHA if revision == 3 else None,
                issuer_id=uid(1) if revision == 3 else None,
                issued_at=TIME if revision == 3 else None,
                reason="自写SQL样例，不代表真实资格",
                created_at=TIME,
            )
        self.insert(
            "compatibility_profiles",
            id=uid(92),
            version=1,
            deliverable_kind="audio",
            tested_versions_json=canonical_json(
                json.loads((ROOT / "tests/fixtures/quality_records.json").read_text())[
                    "CompatibilityProfile"
                ]["tested_versions"]
            ).decode(),
            file_features_json='["aac"]',
            limits_json=canonical_json(
                json.loads((ROOT / "tests/fixtures/quality_records.json").read_text())[
                    "CompatibilityProfile"
                ]["limits"]
            ).decode(),
            status="active",
            created_at=TIME,
        )
        self.insert(
            "exports",
            id=uid(93),
            production_id=uid(11),
            book_id=uid(4),
            packaging_task_id=uid(15),
            candidate_kind="formal_candidate",
            deliverable_kind="audio",
            created_at=TIME,
        )
        self.insert(
            "export_artifacts",
            export_id=uid(93),
            artifact_id=uid(3),
            artifact_sha256=SHA,
        )
        self.db.execute("BEGIN")
        self.insert(
            "issues",
            id=uid(94),
            book_id=uid(4),
            description="自写问题",
            severity="P1",
            status="candidate",
            revision=1,
            created_at=TIME,
        )
        issue = {
            "id": uid(94),
            "book_id": uid(4),
            "description": "自写问题",
            "status": "candidate",
            "severity": "P1",
            "revision": 1,
            "location": None,
            "created_at": TIME,
        }
        self.insert(
            "issue_revisions",
            issue_id=uid(94),
            revision=1,
            snapshot_json=json.dumps(issue, ensure_ascii=False),
            created_at=TIME,
        )
        self.db.execute("COMMIT")
        self.insert(
            "repair_plans",
            id=uid(95),
            version=1,
            issue_id=uid(94),
            issue_revision=1,
            book_id=uid(4),
            base_export_id=uid(93),
            base_artifact_sha256=SHA,
            target_production_id=uid(11),
            retest_cases_json='["自写复现"]',
            created_at=TIME,
        )
        for number in range(1, 6):
            self.insert(
                "evidence_records",
                id=uid(100 + number),
                production_id=uid(11),
                input_artifact_id=uid(3),
                artifact_sha256=SHA,
                binding_id=uid(50),
                scope_id=uid(12),
                risk="D04",
                outcome="pass",
                evidence_kind="tool",
                actor_id=uid(2),
                gate="Q" + str(number),
                case_id="自写门槛样例",
                rule_version="1",
                issue_id=uid(94),
                issue_revision=1,
                plan_id=uid(95),
                plan_version=1,
                created_at=TIME,
            )
        revision = self.db.execute(
            "SELECT quality_revision FROM production_revisions"
        ).fetchone()[0]
        self.insert(
            "quality_snapshots",
            id=uid(96),
            production_id=uid(11),
            revision=revision,
            production_snapshot_sha256=SHA,
            snapshot_sha256=SHA,
            policy_hash=policy_hash,
            report_artifact_id=uid(3),
            qualification_id=uid(91),
            qualification_version=1,
            compatibility_id=uid(92),
            compatibility_version=1,
            created_at=TIME,
        )
        for number in range(1, 6):
            self.insert(
                "gate_results",
                quality_snapshot_id=uid(96),
                gate="Q" + str(number),
                status="pass",
            )
            self.insert(
                "gate_evidence",
                quality_snapshot_id=uid(96),
                gate="Q" + str(number),
                evidence_id=uid(100 + number),
                production_id=uid(11),
            )
        self.insert(
            "repair_proofs",
            id=uid(97),
            issue_id=uid(94),
            plan_id=uid(95),
            plan_version=1,
            candidate_artifact_id=uid(3),
            candidate_sha256=SHA,
            reproduction_evidence_id=uid(104),
            quality_snapshot_id=uid(96),
            production_id=uid(11),
            created_at=TIME,
        )
        self.insert("proof_evidence", proof_id=uid(97), evidence_id=uid(104))
        self.insert(
            "resolution_records",
            id=uid(98),
            issue_id=uid(94),
            issue_revision=1,
            plan_id=uid(95),
            plan_version=1,
            candidate_artifact_id=uid(3),
            candidate_sha256=SHA,
            proof_id=uid(97),
            resolution_kind="resolved_system",
            created_at=TIME,
        )
        self.insert(
            "issue_applicability",
            id=uid(99),
            issue_id=uid(94),
            candidate_artifact_id=uid(3),
            candidate_sha256=SHA,
            scope_id=uid(12),
            environment_json="{}",
            resolution_id=uid(98),
        )
        return dict(
            id=uid(110),
            principal_id=uid(1),
            request_id=uid(111),
            payload_sha256=SHA,
            export_id=uid(93),
            artifact_id=uid(3),
            artifact_sha256=SHA,
            deliverable_kind="audio",
            production_id=uid(11),
            quality_snapshot_id=uid(96),
            qualification_id=uid(91),
            qualification_version=1,
            qualification_event_revision=3,
            revocation_sequence=0,
            compatibility_id=uid(92),
            compatibility_version=1,
            decision="released",
            blockers_json="[]",
            created_at=TIME,
        )

    def test_release_foreign_keys_history_and_revocation_risk(self):
        values = self.seed_delivery()
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("release_decisions", **{**values, "artifact_sha256": "b" * 64})
        self.insert("release_decisions", **values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "release_decisions",
                **{**values, "id": uid(112), "request_id": uid(113)},
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "gate_evidence",
                quality_snapshot_id=uid(96),
                gate="Q1",
                evidence_id=uid(104),
                production_id=uid(11),
            )
        self.insert(
            "qualification_events",
            event_id=uid(204),
            qualification_id=uid(91),
            qualification_version=1,
            revision=4,
            status="revoked",
            revocation_sequence=1,
            dataset_sha256=SHA,
            report_sha256=SHA,
            issuer_id=uid(1),
            issued_at=TIME,
            reason="自写撤销",
            created_at=TIME,
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM release_risk_events").fetchone()[0], 1
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM release_decisions")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM resolution_records")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_new_evidence_invalidates_old_quality_revision(self):
        values = self.seed_delivery()
        before = self.db.execute(
            "SELECT quality_revision FROM production_revisions"
        ).fetchone()[0]
        self.insert(
            "evidence_records",
            id=uid(120),
            production_id=uid(11),
            input_artifact_id=uid(3),
            artifact_sha256=SHA,
            binding_id=uid(50),
            scope_id=uid(12),
            risk="D04",
            outcome="fail",
            evidence_kind="tool",
            actor_id=uid(2),
            gate="Q4",
            case_id="自写反证",
            rule_version="1",
            created_at=TIME,
        )
        self.assertGreater(
            self.db.execute(
                "SELECT quality_revision FROM production_revisions"
            ).fetchone()[0],
            before,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("release_decisions", **values)

    def test_full_migration_failure_and_backup_recovery(self):
        self.seed_delivery()
        directory = Path(self.temp.name) / "upgrade"
        directory.mkdir()
        for path in (ROOT / "migrations").glob("*.sql"):
            (directory / path.name).write_bytes(path.read_bytes())
        (directory / "0004_failure.sql").write_text(
            "CREATE TABLE transient_data (id INTEGER); INSERT INTO no_such_table VALUES (1);"
        )
        with self.assertRaises(sqlite3.OperationalError):
            migrate(self.db, directory)
        self.assertIsNone(
            self.db.execute(
                "SELECT name FROM sqlite_schema WHERE name='transient_data'"
            ).fetchone()
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 3
        )
        backup = connect(Path(self.temp.name) / "backup.sqlite")
        self.addCleanup(backup.close)
        self.db.backup(backup)
        restored = connect(Path(self.temp.name) / "restored.sqlite")
        self.addCleanup(restored.close)
        backup.backup(restored)
        migrate(restored)
        self.assertEqual(
            restored.execute("SELECT count(*) FROM evidence_records").fetchone()[0], 6
        )
        self.assertEqual(restored.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(restored.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_worker_cannot_make_human_review(self):
        self.seed()
        values = dict(
            id=uid(60),
            artifact_id=uid(3),
            artifact_sha256=SHA,
            scope_id=uid(12),
            dimension="自写试听",
            conclusion="uncertain",
            actor_id=uid(2),
            comment="非真实听审",
            created_at=TIME,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("review_records", **values)
        self.insert("review_records", **{**values, "actor_id": uid(1)})

    def test_budget_reservation_unknown_settlement_and_currency(self):
        self.seed()
        self.insert(
            "budget_accounts",
            id=uid(70),
            principal_id=uid(1),
            currency="CNY",
            timezone="Asia/Shanghai",
            daily_limit_minor=3,
            created_at=TIME,
        )
        self.insert(
            "production_budgets",
            production_id=uid(11),
            account_id=uid(70),
            limit_minor=3,
        )

        def entry(n, kind, amount, call="自写调用", currency="CNY"):
            self.insert(
                "budget_ledger",
                id=uid(n),
                account_id=uid(70),
                production_id=uid(11),
                call_id=call,
                entry_kind=kind,
                amount_minor=amount,
                currency=currency,
                local_day="2026-10-18",
                created_at=TIME,
            )

        entry(71, "reserve", 2)
        entry(72, "unknown", 2)
        with self.assertRaises(sqlite3.IntegrityError):
            entry(73, "reserve", 2, "另一调用")
        entry(74, "settle", 1)
        entry(75, "reserve", 2, "另一调用")
        self.assertEqual(
            self.db.execute("SELECT sum(amount_minor) FROM budget_exposure").fetchone()[
                0
            ],
            3,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            entry(76, "settle", 1, "另一调用", currency="USD")
        with self.assertRaises(sqlite3.IntegrityError):
            entry(77, "unknown", 2, "未预留调用")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM budget_ledger")

    def test_daily_budget_is_shared_across_productions(self):
        self.seed()
        self.insert(
            "production_revisions",
            id=uid(150),
            book_id=uid(4),
            text_revision_id=uid(6),
            voice_version_id=uid(10),
            model_revision="自写模型@1",
            config_sha256=self.config_hash,
            snapshot_sha256=SHA,
            created_at=TIME,
        )
        self.insert(
            "budget_accounts",
            id=uid(151),
            principal_id=uid(1),
            currency="CNY",
            timezone="Asia/Shanghai",
            daily_limit_minor=3,
            created_at=TIME,
        )
        for production in (11, 150):
            self.insert(
                "production_budgets",
                production_id=uid(production),
                account_id=uid(151),
                limit_minor=3,
            )
        self.insert(
            "budget_ledger",
            id=uid(152),
            account_id=uid(151),
            production_id=uid(11),
            call_id="自写调用1",
            entry_kind="reserve",
            amount_minor=2,
            currency="CNY",
            local_day="2026-10-18",
            created_at=TIME,
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "每日预算"):
            self.insert(
                "budget_ledger",
                id=uid(153),
                account_id=uid(151),
                production_id=uid(150),
                call_id="自写调用2",
                entry_kind="reserve",
                amount_minor=2,
                currency="CNY",
                local_day="2026-10-18",
                created_at=TIME,
            )

    def test_revocation_before_first_release_is_rejected(self):
        values = self.seed_delivery()
        self.insert(
            "qualification_events",
            event_id=uid(204),
            qualification_id=uid(91),
            qualification_version=1,
            revision=4,
            status="revoked",
            revocation_sequence=1,
            dataset_sha256=SHA,
            report_sha256=SHA,
            issuer_id=uid(1),
            issued_at=TIME,
            reason="自写撤销",
            created_at=TIME,
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "资格配置失效"):
            self.insert("release_decisions", **values)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM release_decisions").fetchone()[0], 0
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM release_risk_events").fetchone()[0], 0
        )

    def test_auxiliary_references_and_upload_completion(self):
        self.seed()
        self.attempt(1, "b")
        self.insert("artifact_owners", artifact_id=uid(3), principal_id=uid(1))
        self.insert(
            "auth_tokens",
            id=uid(160),
            principal_id=uid(2),
            token_sha256="d" * 64,
            purpose="worker",
            created_at=TIME,
        )
        self.insert(
            "browser_sessions",
            id=uid(161),
            principal_id=uid(1),
            session_sha256="e" * 64,
            csrf_sha256="f" * 64,
            expires_at=TIME,
            created_at=TIME,
        )
        self.insert(
            "pairing_codes",
            principal_id=uid(1),
            code_sha256="e" * 64,
            expires_at=TIME,
            created_at=TIME,
        )
        self.insert(
            "text_mappings",
            id=uid(162),
            book_id=uid(4),
            from_revision_id=uid(6),
            to_revision_id=uid(6),
            unit_id=uid(8),
            source_artifact_id=uid(3),
            display_artifact_id=uid(3),
            spoken_artifact_id=uid(3),
            comparison_artifact_id=uid(3),
            transform_kind="自写映射",
            start_offset=0,
            end_offset=10,
        )
        self.insert(
            "scope_units", scope_id=uid(12), production_id=uid(11), unit_id=uid(8)
        )
        self.insert(
            "synthesis_blocks",
            id=uid(163),
            production_id=uid(11),
            position=0,
            input_sha256=SHA,
            rules_version="1",
        )
        self.insert(
            "sentence_links",
            block_id=uid(163),
            production_id=uid(11),
            sentence_id=uid(8),
            sequence=0,
            start_offset=0,
            end_offset=10,
        )
        self.insert("task_inputs", task_id=uid(15), artifact_id=uid(3))
        self.insert("task_outputs", task_id=uid(15), artifact_id=uid(3))
        self.insert(
            "dependency_nodes",
            id=uid(164),
            production_id=uid(11),
            kind="task",
            task_id=uid(15),
        )
        self.insert(
            "dependency_nodes",
            id=uid(165),
            production_id=uid(11),
            kind="artifact",
            artifact_id=uid(3),
        )
        self.insert(
            "dependency_edges",
            production_id=uid(11),
            node_id=uid(164),
            depends_on_id=uid(165),
        )
        self.insert(
            "uploads",
            id=uid(166),
            principal_id=uid(1),
            size_bytes=100,
            sha256=SHA,
            chunk_size_bytes=128,
            media_type="application/json",
            purpose="evidence",
            state="open",
            expires_at=TIME,
            created_at=TIME,
        )
        self.insert(
            "upload_chunks",
            upload_id=uid(166),
            chunk_index=0,
            size_bytes=100,
            sha256=SHA,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE uploads SET size_bytes=99,state='completed',artifact_id=?",
                (uid(3),),
            )
        self.db.execute("UPDATE uploads SET state='completed',artifact_id=?", (uid(3),))
        self.db.execute("UPDATE artifacts SET validation_status='invalid'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "未校验制品"):
            self.insert(
                "result_receipts",
                id=uid(167),
                task_id=uid(15),
                attempt_no=1,
                principal_id=uid(2),
                request_id=uid(168),
                payload_sha256=SHA,
                result_summary="自写摘要",
                accepted_at=TIME,
            )
        self.db.execute("UPDATE artifacts SET validation_status='validated'")
        self.insert(
            "audit_events",
            id=uid(169),
            principal_id=uid(1),
            operation="自写检查",
            target_kind="book",
            target_id=uid(4),
            revision=1,
            created_at=TIME,
        )
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_issue_revision_history_and_agent_action_idempotency(self):
        self.seed()
        self.db.execute("BEGIN")
        self.insert(
            "issues",
            id=uid(80),
            book_id=uid(4),
            description="自写问题",
            severity="P1",
            status="awaiting_location",
            revision=1,
            created_at=TIME,
        )
        self.insert(
            "issue_revisions",
            issue_id=uid(80),
            revision=1,
            snapshot_json=json.dumps(
                {
                    "id": uid(80),
                    "book_id": uid(4),
                    "description": "自写问题",
                    "status": "awaiting_location",
                    "severity": "P1",
                    "revision": 1,
                    "location": None,
                    "created_at": TIME,
                },
                ensure_ascii=False,
            ),
            created_at=TIME,
        )
        self.db.execute("COMMIT")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM issue_revisions")
        self.insert(
            "agent_runs",
            id=uid(81),
            production_id=uid(11),
            snapshot_sha256=SHA,
            policy_hash=None,
            principal_id=uid(1),
            scope_id=uid(12),
            provider_id="自写供应商",
            model_revision="自写模型",
            template_version="1",
            schema_version="1",
            state="queued",
            created_at=TIME,
        )
        self.insert(
            "agent_steps",
            run_id=uid(81),
            step_sequence=1,
            decision_artifact_id=uid(3),
            created_at=TIME,
        )
        values = dict(
            id=uid(82),
            run_id=uid(81),
            step_sequence=1,
            principal_id=uid(1),
            production_id=uid(11),
            action_key="自写唯一动作",
            tool_version="1",
            payload_sha256=SHA,
            result_json="{}",
            created_at=TIME,
        )
        self.insert("tool_receipts", **values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert("tool_receipts", **{**values, "id": uid(83)})
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(
                "agent_steps",
                run_id=uid(81),
                step_sequence=1,
                decision_artifact_id=uid(3),
                created_at=TIME,
            )


if __name__ == "__main__":
    unittest.main()
