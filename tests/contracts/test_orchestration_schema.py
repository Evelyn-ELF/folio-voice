"""I0 编排结构用例；不验证租约时效、权限或数据库事务。"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
ID = "11111111-1111-4111-8111-111111111111"
OTHER_ID = "22222222-2222-4222-8222-222222222222"
SHA = "a" * 64


def requests():
    """按系统设计10.6手写输入，不从生成器或Schema构造预期。"""
    authorization = {
        "attempt_no": 1,
        "lease_token": "仅用于测试的租约令牌",
        "input_snapshot_sha256": SHA,
        "app_generation": ID,
    }
    return {
        "CreateProduction": {
            "book_id": ID,
            "text_revision_id": ID,
            "voice_version_id": ID,
            "model_revision": "自写测试模型@固定修订",
            "config_sha256": SHA,
            "scope": [ID, OTHER_ID],
            "request_id": ID,
        },
        "ProductionAccepted": {
            "production_id": ID,
            "control_revision": 1,
            "status_url": f"/api/v1/productions/{ID}",
        },
        "TaskLease": {
            **authorization,
            "task_id": ID,
            "production_id": ID,
            "expires_at": "2026-10-17T12:00:00+00:00",
            "control_revision": 1,
            "input_artifacts": [{"artifact_id": ID, "size_bytes": 0, "sha256": SHA}],
        },
        "Heartbeat": authorization,
        "CheckpointCommand": {
            **authorization,
            "request_id": ID,
            "checkpoint_artifact_id": ID,
            "completed_unit_ids": [ID],
        },
        "TaskResult": {
            **authorization,
            "request_id": ID,
            "output_artifact_ids": [ID],
            "result_summary": "自写测试单元已执行；质量另行检查。",
        },
        "ProductionControl": {"request_id": ID, "expected_control_revision": 1},
        "CheckpointManifest": {
            "input_snapshot_sha256": SHA,
            "adapter_version": "测试适配器@1",
            "completed_unit_ids": [ID],
            "artifacts": [
                {
                    "unit_id": ID,
                    "artifacts": [{"artifact_id": ID, "size_bytes": 10, "sha256": SHA}],
                }
            ],
            "pending_unit_ids": [OTHER_ID],
            "cursor": "下一完整单元",
        },
    }


class OrchestrationSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "docs/contracts/core.schema.json").read_text())

    def validator(self, name):
        self.assertIn(name, self.schema["$defs"], f"缺少编排结构契约：{name}")
        schema = {key: value for key, value in self.schema.items() if key != "oneOf"}
        schema["$ref"] = f"#/$defs/{name}"
        return Draft202012Validator(schema, format_checker=FormatChecker())

    def test_valid_orchestration_payloads(self):
        for name, payload in requests().items():
            with self.subTest(name=name):
                self.assertEqual(list(self.validator(name).iter_errors(payload)), [])

    def test_unknown_fields_cannot_inject_authority_or_completion(self):
        for name, payload in requests().items():
            with self.subTest(name=name):
                forged = dict(payload, actor="maintainer", passed=True)
                self.assertTrue(list(self.validator(name).iter_errors(forged)))

    def test_every_documented_field_is_required(self):
        for name, payload in requests().items():
            for field in payload:
                with self.subTest(name=name, field=field):
                    incomplete = payload.copy()
                    del incomplete[field]
                    self.assertTrue(list(self.validator(name).iter_errors(incomplete)))

    def test_invalid_identifiers_ranges_and_versions_are_rejected(self):
        cases = [
            ("CreateProduction", "scope", []),
            ("CreateProduction", "scope", [ID, ID]),
            ("CreateProduction", "book_id", "私人书籍文件名"),
            ("CreateProduction", "config_sha256", "A" * 64),
            ("TaskLease", "expires_at", "2026-10-17T12:00:00"),
            ("TaskLease", "expires_at", "2026-02-30T12:00:00Z"),
            ("TaskLease", "control_revision", 0),
            ("Heartbeat", "attempt_no", 0),
            ("Heartbeat", "attempt_no", True),
            ("Heartbeat", "lease_token", ""),
            ("Heartbeat", "app_generation", "旧世代"),
            ("TaskResult", "output_artifact_ids", [ID, ID]),
            ("ProductionControl", "expected_control_revision", -1),
        ]
        for name, field, value in cases:
            with self.subTest(name=name, field=field, value=value):
                payload = copy.deepcopy(requests()[name])
                payload[field] = value
                self.assertTrue(list(self.validator(name).iter_errors(payload)))

    def test_nested_artifact_lengths_and_unknown_fields_are_rejected(self):
        for field, value in (
            ("size_bytes", -1),
            ("sha256", "损坏散列"),
            ("path", "/私人路径"),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(requests()["TaskLease"])
                payload["input_artifacts"][0][field] = value
                self.assertTrue(list(self.validator("TaskLease").iter_errors(payload)))

    def test_utc_offset_is_accepted_and_input_order_preserved(self):
        payload = requests()["TaskLease"]
        payload["expires_at"] = "2026-10-17T20:00:00+08:00"
        self.assertEqual(list(self.validator("TaskLease").iter_errors(payload)), [])
        payload = requests()["CreateProduction"]
        self.validator("CreateProduction").validate(payload)
        self.assertEqual(payload["scope"], [ID, OTHER_ID])

    def test_public_envelopes_validate_against_root_schema(self):
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        for name, payload in requests().items():
            with self.subTest(name=name):
                self.assertEqual(list(validator.iter_errors(payload)), [])


if __name__ == "__main__":
    unittest.main()
