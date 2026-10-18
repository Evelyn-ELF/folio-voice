"""质量记录的结构验证；自写数据不能证明真实评估或授权。"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
ID = "11111111-1111-4111-8111-111111111111"
SHA = "a" * 64
TIME = "2026-10-17T00:00:00Z"


def records():
    """自写固定样例，不从待测Schema生成；每次独立读取避免测试间污染。"""
    return json.loads((ROOT / "tests/fixtures/quality_records.json").read_text())


class QualitySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "docs/contracts/core.schema.json").read_text())

    def valid(self, name, data):
        schema = {"$defs": self.schema["$defs"], "$ref": f"#/$defs/{name}"}
        return Draft202012Validator(
            schema, format_checker=FormatChecker(formats=["uuid", "date-time"])
        ).is_valid(data)

    def test_records_and_public_union(self):
        for name, data in records().items():
            with self.subTest(name=name):
                self.assertTrue(self.valid(name, data))
                self.assertTrue(Draft202012Validator(self.schema).is_valid(data))

    def test_missing_and_unknown_fields(self):
        for name, data in records().items():
            for field in data:
                candidate = copy.deepcopy(data)
                del candidate[field]
                with self.subTest(name=name, field=field):
                    self.assertFalse(self.valid(name, candidate))
            self.assertFalse(self.valid(name, {**data, "passed": True}))

    def test_active_qualification_requires_report_and_issuer(self):
        data = records()["Qualification"]
        data.update(status="active", revision=3)
        self.assertFalse(self.valid("Qualification", data))
        data.update(dataset_sha256=SHA, report_sha256=SHA, issuer_id=ID, issued_at=TIME)
        self.assertTrue(self.valid("Qualification", data))
        data.update(status="suspended")
        self.assertFalse(self.valid("Qualification", data))
        data["revocation_sequence"] = 1
        self.assertTrue(self.valid("Qualification", data))
        data["status"] = "active"
        self.assertFalse(self.valid("Qualification", data))

    def test_release_cannot_omit_gate_or_version_or_hide_blocker(self):
        data = records()["ReleaseDecision"]
        data.update(decision="released", blockers=[])
        self.assertFalse(self.valid("ReleaseDecision", data))
        data["gate_evidence"] = {gate: [ID] for gate in ("Q1", "Q2", "Q3", "Q4", "Q5")}
        data["qualification"] = {
            "id": ID,
            "version": 1,
            "policy_hash": SHA,
            "revocation_sequence": 0,
        }
        data["compatibility_profile"] = {"id": ID, "version": 1}
        self.assertTrue(self.valid("ReleaseDecision", data))
        for gate in data["gate_evidence"]:
            changed = copy.deepcopy(data)
            changed["gate_evidence"][gate] = []
            self.assertFalse(self.valid("ReleaseDecision", changed))
        data["blockers"] = [{"code": "REVIEW_REQUIRED", "detail": "未解决"}]
        self.assertFalse(self.valid("ReleaseDecision", data))

    def test_exact_versions_scopes_and_decimal_thresholds(self):
        data = records()["QualityPolicy"]
        config = data["config"]
        threshold = config["required_detectors"][0]["thresholds"][0]
        for value in (0.1, "01", "-0", "1.0", "1e-3", "NaN"):
            threshold["value"] = value
            self.assertFalse(self.valid("QualityPolicy", data), value)
        for value in ("0", "-0.1", "12.001"):
            threshold["value"] = value
            self.assertTrue(self.valid("QualityPolicy", data), value)
        threshold["regression_tolerance"] = "-0.1"
        self.assertFalse(self.valid("QualityPolicy", data))
        threshold["regression_tolerance"] = "0"
        config["applicability"]["voice_version_ids"] = []
        self.assertFalse(self.valid("QualityPolicy", data))
        profile = records()["CompatibilityProfile"]
        profile["tested_versions"][0]["os_version_range"] = ">=1"
        self.assertFalse(self.valid("CompatibilityProfile", profile))

    def test_policy_digest_rejects_trailing_newline(self):
        data = records()["QualityPolicy"]
        for value in (SHA + "\n", "A" * 64, "a" * 63):
            data["policy_hash"] = value
            with self.subTest(value=repr(value)):
                self.assertFalse(self.valid("QualityPolicy", data))

    def test_no_authority_or_budget_bypass_in_policy(self):
        data = records()["QualityPolicy"]
        data["config"]["qualification_id"] = ID
        self.assertFalse(self.valid("QualityPolicy", data))
        del data["config"]["qualification_id"]
        data["config"]["budget_rules"]["tts_generations_per_block"] = 4
        self.assertFalse(self.valid("QualityPolicy", data))


if __name__ == "__main__":
    unittest.main()
