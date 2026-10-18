"""真实SQLite约束、失败原子性与备份回退；不代表服务权限测试。"""

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from packages.adapters.sqlite_migrations import connect, migrate
from packages.core.canonical import canonical_json, configuration_hash

ROOT = Path(__file__).resolve().parents[2]
ID = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
SHA = "a" * 64
TIME = "2026-10-17T00:00:00Z"


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "database.sqlite"
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        # 这组历史回归固定验证0001，完整升级链另由领域迁移测试覆盖。
        self.baseline = Path(self.temp.name) / "baseline"
        self.baseline.mkdir()
        shutil.copyfile(
            ROOT / "migrations/0001_quality_registry.sql",
            self.baseline / "0001_quality_registry.sql",
        )
        migrate(self.db, self.baseline)
        self.fixture = json.loads(
            (ROOT / "tests/fixtures/quality_records.json").read_text()
        )
        self.config = self.fixture["QualityPolicy"]["config"]
        self.policy_hash = configuration_hash(self.config)

    def seed(self):
        self.db.execute(
            "INSERT INTO policy_configs VALUES (?, ?)",
            (self.policy_hash, canonical_json(self.config).decode()),
        )
        self.db.execute(
            "INSERT INTO quality_policies VALUES (?, 1, ?, ?)",
            (ID, self.policy_hash, TIME),
        )
        self.db.execute(
            "INSERT INTO qualification_versions VALUES (?, 1, ?, ?, ?, ?)",
            (
                ID,
                self.policy_hash,
                canonical_json(self.fixture["Qualification"]["scope"]).decode(),
                '["detector"]',
                TIME,
            ),
        )

    def event(self, revision, status, sequence=0, report=False, **overrides):
        fields = {
            "event_id": f"00000000-0000-4000-8000-{revision:012d}",
            "qualification_id": ID,
            "qualification_version": 1,
            "revision": revision,
            "status": status,
            "revocation_sequence": sequence,
            "dataset_sha256": SHA if report else None,
            "report_sha256": SHA if report else None,
            "issuer_id": OTHER if report else None,
            "issued_at": TIME if report else None,
            "reason": "自写迁移测试，无真实资格",
            "created_at": TIME,
        }
        fields.update(overrides)
        self.db.execute(
            f"INSERT INTO qualification_events ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
            tuple(fields.values()),
        )

    def activate(self):
        self.event(1, "draft")
        self.event(2, "evaluating")
        self.event(3, "active", report=True)
        self.db.execute(
            "INSERT INTO active_qualifications VALUES (?, ?, 1, 3)",
            (self.policy_hash, ID),
        )

    def test_migration_is_idempotent_and_enables_foreign_keys(self):
        before = self.db.execute("SELECT * FROM schema_migrations").fetchall()
        migrate(self.db, self.baseline)
        self.assertEqual(
            before, self.db.execute("SELECT * FROM schema_migrations").fetchall()
        )
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO quality_policies VALUES (?, 1, ?, ?)", (ID, SHA, TIME)
            )

    def test_policy_hash_unique_and_immutable(self):
        self.seed()
        for sql, args in (
            (
                "INSERT INTO policy_configs VALUES (?, ?)",
                (SHA, canonical_json(self.config).decode()),
            ),
            (
                "INSERT INTO quality_policies VALUES (?, 1, ?, ?)",
                (ID, self.policy_hash, TIME),
            ),
            ("UPDATE quality_policies SET version=2", ()),
            ("DELETE FROM policy_configs", ()),
            (
                "INSERT OR REPLACE INTO quality_policies VALUES (?, 1, ?, ?)",
                (ID, self.policy_hash, TIME),
            ),
            ("UPDATE qualification_versions SET scope_json='[]'", ()),
        ):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql, args)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM quality_policies").fetchone()[0], 1
        )

    def test_lifecycle_revocation_and_selection(self):
        self.seed()
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(1, "active", report=True)
        self.event(1, "draft")
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(2, "active", report=True)
        self.event(2, "evaluating")
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(3, "active")
        self.event(3, "evaluating", report=True)  # 失败评估保留，不获得活动资格。
        self.event(4, "active", report=True)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO active_qualifications VALUES (?, ?, 1, 3)",
                (self.policy_hash, ID),
            )
        self.db.execute(
            "INSERT INTO active_qualifications VALUES (?, ?, 1, 4)",
            (self.policy_hash, ID),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(5, "suspended", report=True)
        self.event(5, "suspended", 1, True)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM active_qualifications").fetchone()[0],
            0,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(6, "active", 0, True)
        self.event(6, "revoked", 2, True)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(7, "evaluating")
        self.assertEqual(
            self.db.execute(
                "SELECT status, revocation_sequence FROM current_qualifications"
            ).fetchone(),
            ("revoked", 2),
        )

    def test_revocation_and_deselection_share_one_transaction(self):
        self.seed()
        self.activate()
        self.db.execute("BEGIN")
        self.event(4, "revoked", 1, True)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM active_qualifications").fetchone()[0],
            0,
        )
        self.db.execute("ROLLBACK")
        self.assertEqual(
            self.db.execute("SELECT status FROM current_qualifications").fetchone()[0],
            "active",
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM active_qualifications").fetchone()[0],
            1,
        )
        self.event(4, "revoked", 1, True)
        self.assertEqual(
            self.db.execute(
                "SELECT status, revocation_sequence FROM current_qualifications"
            ).fetchone(),
            ("revoked", 1),
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM active_qualifications").fetchone()[0],
            0,
        )

    def test_canonical_config_and_scope_are_enforced(self):
        self.seed()
        other_config = json.loads(json.dumps(self.config))
        other_config["budget_rules"]["request_timeout_seconds"] = 119
        other_hash = configuration_hash(other_config)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO policy_configs VALUES (?, ?)",
                (other_hash, json.dumps(other_config)),
            )
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute(
                "INSERT INTO policy_configs VALUES (?, ?)",
                (SHA, '{"contract_version":2,"canonicalization":"fv-json-v1","x":1.0}'),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO qualification_versions VALUES (?, 1, ?, ?, ?, ?)",
                (OTHER, self.policy_hash, "[]", '["detector"]', TIME),
            )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM policy_configs").fetchone()[0], 1
        )

    def test_history_cannot_be_replaced_deleted_or_rebound(self):
        self.seed()
        self.activate()
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(4, "revoked", 1, True, report_sha256="b" * 64)
        for sql in (
            "DELETE FROM qualification_events",
            "UPDATE qualification_events SET reason='覆盖'",
            "DELETE FROM qualification_versions",
        ):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(5, "revoked", 1, True)  # 不允许跳过revision。
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM qualification_events").fetchone()[0],
            3,
        )

    def test_failed_upgrade_rolls_back_ddl_data_and_version(self):
        self.seed()
        directory = Path(self.temp.name) / "migrations"
        directory.mkdir()
        first = ROOT / "migrations/0001_quality_registry.sql"
        (directory / first.name).write_bytes(first.read_bytes())
        (directory / "0002_broken.sql").write_text(
            "CREATE TABLE temporary_upgrade (id INTEGER); INSERT INTO temporary_upgrade VALUES (1); INSERT INTO absent_table VALUES (1);"
        )
        with self.assertRaises(sqlite3.OperationalError):
            migrate(self.db, directory)
        self.assertIsNone(
            self.db.execute(
                "SELECT name FROM sqlite_schema WHERE name='temporary_upgrade'"
            ).fetchone()
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1
        )
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM quality_policies").fetchone()[0], 1
        )
        self.assertFalse(self.db.in_transaction)

    def test_applied_migration_hash_and_newer_database_are_rejected(self):
        directory = Path(self.temp.name) / "migrations"
        directory.mkdir()
        target = directory / "0001_quality_registry.sql"
        original = (ROOT / "migrations" / target.name).read_text()
        target.write_text(original + "\n-- 已被修改\n")
        with self.assertRaisesRegex(ValueError, "散列"):
            migrate(self.db, directory)
        target.unlink()
        with self.assertRaisesRegex(ValueError, "版本"):
            migrate(self.db, directory)

    def test_transaction_control_in_migration_cannot_break_atomicity(self):
        directory = Path(self.temp.name) / "migrations"
        directory.mkdir()
        first = ROOT / "migrations/0001_quality_registry.sql"
        (directory / first.name).write_bytes(first.read_bytes())
        (directory / "0002_escape.sql").write_text(
            "CREATE TABLE escape (id INTEGER); COMMIT;"
        )
        with self.assertRaises(sqlite3.DatabaseError):
            migrate(self.db, directory)
        self.assertIsNone(
            self.db.execute(
                "SELECT name FROM sqlite_schema WHERE name='escape'"
            ).fetchone()
        )

    def test_backup_restores_preupgrade_state(self):
        self.seed()
        self.activate()
        backup = connect(Path(self.temp.name) / "backup.sqlite")
        self.addCleanup(backup.close)
        self.db.backup(backup)
        directory = Path(self.temp.name) / "upgrade"
        directory.mkdir()
        first = ROOT / "migrations/0001_quality_registry.sql"
        (directory / first.name).write_bytes(first.read_bytes())
        (directory / "0002_upgrade.sql").write_text(
            "CREATE TABLE upgrade_marker (id INTEGER); INSERT INTO upgrade_marker VALUES (1);"
        )
        migrate(self.db, directory)
        with self.assertRaisesRegex(ValueError, "版本"):
            migrate(self.db, self.baseline)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 2
        )
        restored = connect(Path(self.temp.name) / "restored.sqlite")
        self.addCleanup(restored.close)
        backup.backup(restored)
        migrate(restored, self.baseline)
        self.assertEqual(
            restored.execute("SELECT status FROM current_qualifications").fetchone()[0],
            "active",
        )
        self.assertEqual(
            restored.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1
        )
        self.assertIsNone(
            restored.execute(
                "SELECT name FROM sqlite_schema WHERE name='upgrade_marker'"
            ).fetchone()
        )
        self.assertEqual(restored.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(restored.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_existing_transaction_and_unknown_database_are_rejected(self):
        self.db.execute("BEGIN")
        with self.assertRaises(ValueError):
            migrate(self.db, self.baseline)
        self.db.execute("ROLLBACK")
        unknown = connect(Path(self.temp.name) / "unknown.sqlite")
        self.addCleanup(unknown.close)
        unknown.execute("CREATE TABLE existing (id INTEGER)")
        with self.assertRaises(ValueError):
            migrate(unknown, self.baseline)


if __name__ == "__main__":
    unittest.main()
