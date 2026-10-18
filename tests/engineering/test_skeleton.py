"""只验证工程骨架，不代替产品服务用例。"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[2]


class SkeletonTests(unittest.TestCase):
    def test_health_live_and_problem_responses_match_contract(self):
        schema = json.loads((ROOT / "docs/contracts/core.schema.json").read_text())
        with TestClient(create_app()) as client:
            for path, status, model in [
                ("/api/v1/health/live", 200, "HealthLive"),
                ("/api/v1/health/ready", 401, "ProblemDetails"),
                ("/api/v1/productions", 404, "ProblemDetails"),
            ]:
                response = client.get(path)
                self.assertEqual(response.status_code, status)
                Draft202012Validator(
                    {"$ref": f"#/$defs/{model}", "$defs": schema["$defs"]},
                    format_checker=Draft202012Validator.FORMAT_CHECKER,
                ).validate(response.json())
                if status != 200:
                    self.assertEqual(
                        response.headers["content-type"], "application/problem+json"
                    )
            self.assertEqual(client.get("/openapi.json").status_code, 404)
            self.assertEqual(
                client.post("/api/v1/productions", json={}).status_code, 404
            )

    def test_worker_entrypoints_do_not_claim_capabilities(self):
        for name in ("container", "macos"):
            result = subprocess.run(
                [sys.executable, "-m", f"workers.{name}.main", "--diagnose"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value["就绪"])
            self.assertEqual(value["能力"], [])
            result = subprocess.run(
                [sys.executable, "-m", f"workers.{name}.main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
