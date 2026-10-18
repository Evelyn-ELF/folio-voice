"""对独立契约副本运行真实CLI，验证失败确实阻断且不写回文件。"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/validate_http_contract.py"


class HttpValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contracts = self.root / "docs/contracts"
        self.contracts.mkdir(parents=True)
        for name in (
            "core.schema.json",
            "openapi.json",
            "http_examples.json",
            "http_response_examples.json",
        ):
            shutil.copyfile(ROOT / "docs/contracts" / name, self.contracts / name)

    def run_check(self, expected):
        before = {p.name: p.read_bytes() for p in self.contracts.glob("*.json")}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in self.contracts.glob("*.json")}
        )
        return json.loads(result.stdout)

    def edit(self, name, action):
        p = self.contracts / name
        data = json.loads(p.read_text())
        action(data)
        p.write_text(json.dumps(data, ensure_ascii=False))

    def test_current_contract_passes_read_only(self):
        self.assertEqual(self.run_check(0)["操作数"], 48)

    def test_missing_csrf_and_external_reference_fail(self):
        self.edit(
            "openapi.json",
            lambda d: d["paths"]["/books"]["post"].update(
                security=[{"BrowserSession": []}]
            ),
        )
        self.assertIn("CSRF", self.run_check(1)["错误"])
        shutil.copyfile(
            ROOT / "docs/contracts/openapi.json", self.contracts / "openapi.json"
        )
        self.edit(
            "openapi.json", lambda d: d["paths"]["/tasks/{id}"]["get"].pop("security")
        )
        self.assertIn("显式认证", self.run_check(1)["错误"])
        shutil.copyfile(
            ROOT / "docs/contracts/openapi.json", self.contracts / "openapi.json"
        )
        self.edit(
            "openapi.json",
            lambda d: d["components"]["schemas"].update(
                UUID={"$ref": "https://invalid.test/schema.json"}
            ),
        )
        self.assertIn("本地契约", self.run_check(1)["错误"])
        shutil.copyfile(
            ROOT / "docs/contracts/openapi.json", self.contracts / "openapi.json"
        )
        self.edit(
            "core.schema.json",
            lambda d: d["$defs"]["UUID"].update(
                {"$dynamicRef": "https://invalid.test/remote"}
            ),
        )
        self.assertIn("本地契约", self.run_check(1)["错误"])

    def test_injected_actor_and_wrong_problem_status_fail(self):
        self.edit(
            "http_examples.json", lambda d: d[0]["data"].update(actor="maintainer")
        )
        self.assertEqual(self.run_check(1)["结果"], "失败")
        shutil.copyfile(
            ROOT / "docs/contracts/http_examples.json",
            self.contracts / "http_examples.json",
        )
        self.edit(
            "http_response_examples.json", lambda d: d[-1]["data"].update(status=409)
        )
        self.assertIn("状态", self.run_check(1)["错误"])

    def test_missing_source_fails_without_recreating_it(self):
        (self.contracts / "core.schema.json").unlink()
        self.assertEqual(self.run_check(1)["结果"], "失败")


if __name__ == "__main__":
    unittest.main()
