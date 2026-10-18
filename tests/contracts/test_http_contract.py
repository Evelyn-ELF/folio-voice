"""HTTP结构与路由契约；不启动服务，不代替实际权限或竞态测试。"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import OpenAPIV31SpecValidator

from tools.validate_http_contract import audit

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    ("post", "/sessions"),
    ("delete", "/sessions/current"),
    ("post", "/uploads"),
    ("get", "/uploads/{id}"),
    ("put", "/uploads/{id}/chunks/{index}"),
    ("post", "/uploads/{id}/complete"),
    ("get", "/artifacts/{id}"),
    ("post", "/books"),
    ("post", "/books/{id}/imports"),
    ("get", "/books/{id}/revisions"),
    ("post", "/books/{id}/revisions"),
    ("post", "/voices"),
    ("post", "/voices/{id}/versions"),
    ("post", "/productions"),
    ("get", "/productions/{id}"),
    ("get", "/productions/{id}/quality"),
    ("get", "/productions/{id}/resume-manifest"),
    ("post", "/productions/{id}/pause"),
    ("post", "/productions/{id}/resume"),
    ("post", "/productions/{id}/cancel"),
    ("get", "/tasks/{id}"),
    ("post", "/tasks/{id}/pause"),
    ("post", "/tasks/{id}/resume"),
    ("post", "/tasks/{id}/cancel"),
    ("post", "/tasks/{id}/retry"),
    ("post", "/workers/register"),
    ("post", "/workers/{id}/claims"),
    ("post", "/tasks/{id}/heartbeat"),
    ("post", "/tasks/{id}/results"),
    ("post", "/tasks/{id}/checkpoints"),
    ("post", "/reviews"),
    ("post", "/exports"),
    ("get", "/health/live"),
    ("get", "/health/ready"),
    ("post", "/productions/{id}/agent-runs"),
    ("get", "/agent-runs/{id}"),
    ("post", "/agent-runs/{id}/cancel"),
    ("post", "/repair-proposals/{id}/apply"),
    ("post", "/quality-policies/{id}/qualify"),
    ("post", "/qualifications/{id}/revoke"),
    ("post", "/exports/{id}/release"),
    ("post", "/issues"),
    ("post", "/issues/{id}/locate"),
    ("post", "/issues/{id}/repair-plans"),
    ("post", "/issues/{id}/evidence"),
    ("post", "/issues/{id}/resolve"),
    ("post", "/issues/{id}/confirm"),
    ("post", "/issues/{id}/reopen"),
}


class HttpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "docs/contracts/openapi.json"
        cls.api = json.loads(cls.path.read_text())
        cls.core = json.loads((ROOT / "docs/contracts/core.schema.json").read_text())

    def test_standard_and_complete_operation_set(self):
        errors = list(
            OpenAPIV31SpecValidator(self.api, base_uri=self.path.as_uri()).iter_errors()
        )
        self.assertEqual(errors, [])
        actual = {
            (method, path)
            for path, item in self.api["paths"].items()
            for method in item
            if method in ("get", "post", "put", "delete")
        }
        self.assertEqual(actual, EXPECTED)
        operations = [
            self.api["paths"][path][method]["operationId"] for method, path in EXPECTED
        ]
        self.assertEqual(len(operations), len(set(operations)))

    def test_authentication_roles_csrf_and_problem_responses(self):
        for method, path in EXPECTED:
            operation = self.api["paths"][path][method]
            with self.subTest(method=method, path=path):
                if path not in ("/sessions", "/health/live"):
                    self.assertTrue(operation["security"])
                    self.assertIn("401", operation["responses"])
                    self.assertIn("403", operation["responses"])
                for code, response in operation["responses"].items():
                    if int(code) >= 400:
                        self.assertIn("application/problem+json", response["content"])
                if method != "get":
                    for alternative in operation["security"]:
                        if "BrowserSession" in alternative:
                            self.assertIn("CsrfToken", alternative)
        for path in (
            "/reviews",
            "/quality-policies/{id}/qualify",
            "/issues/{id}/confirm",
        ):
            operation = self.api["paths"][path]["post"]
            self.assertFalse(any("WorkerToken" in s for s in operation["security"]))
            self.assertEqual(operation["x-actor-kind"], "human")
        self.assertIn(
            "maintainer",
            self.api["paths"]["/quality-policies/{id}/qualify"]["post"][
                "x-allowed-roles"
            ],
        )

    def test_core_reference_identity_and_conditional_update(self):
        for name, schema in self.api["components"]["schemas"].items():
            self.assertEqual(schema, {"$ref": f"core.schema.json#/$defs/{name}"})
            self.assertIn(name, self.core["$defs"])
        for path in (
            "/books/{id}/revisions",
            "/repair-proposals/{id}/apply",
            "/issues/{id}/locate",
            "/issues/{id}/repair-plans",
            "/issues/{id}/resolve",
            "/issues/{id}/confirm",
            "/issues/{id}/reopen",
        ):
            operation = self.api["paths"][path]["post"]
            self.assertTrue(
                any(
                    p.get("name") == "If-Match" and p["required"]
                    for p in operation["parameters"]
                )
            )
            self.assertIn("412", operation["responses"])
            self.assertIn("409", operation["responses"])

    def test_transport_and_no_task_lease_in_no_content_response(self):
        claim = self.api["paths"]["/workers/{id}/claims"]["post"]["responses"]
        self.assertEqual(
            claim["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/TaskLease",
        )
        self.assertNotIn("content", claim["204"])
        upload = self.api["paths"]["/uploads/{id}/chunks/{index}"]["put"]
        self.assertIn("application/octet-stream", upload["requestBody"]["content"])
        artifact = self.api["paths"]["/artifacts/{id}"]["get"]
        self.assertIn(
            "application/octet-stream", artifact["responses"]["200"]["content"]
        )
        self.assertIn("206", artifact["responses"])
        self.assertIn("416", artifact["responses"])
        self.assertEqual(self.api["servers"], [{"url": "/api/v1"}])

    def test_request_examples_required_fields_and_no_injected_actor(self):
        cases = json.loads((ROOT / "docs/contracts/http_examples.json").read_text())
        for case in cases:
            name, data = case["schema"], case["data"]
            scoped = {"$defs": self.core["$defs"], "$ref": f"#/$defs/{name}"}
            validator = Draft202012Validator(
                scoped, format_checker=FormatChecker(formats=["uuid", "date-time"])
            )
            with self.subTest(name=case["name"]):
                self.assertTrue(
                    validator.is_valid(data), list(validator.iter_errors(data))
                )
                for field in self.core["$defs"][name]["required"]:
                    bad = copy.deepcopy(data)
                    del bad[field]
                    self.assertFalse(validator.is_valid(bad), field)
                self.assertFalse(validator.is_valid({**data, "actor": "maintainer"}))
                self.assertFalse(validator.is_valid({**data, "passed": True}))
        covered = {case["schema"] for case in cases}
        requests = set()
        for method, path in EXPECTED:
            op = self.api["paths"][path][method]
            body = op.get("requestBody", {}).get("content", {}).get("application/json")
            if body:
                requests.add(body["schema"]["$ref"].split("/")[-1])
        self.assertTrue(requests <= covered, requests - covered)

    def test_response_examples_match_operation_and_status(self):
        cases = json.loads(
            (ROOT / "docs/contracts/http_response_examples.json").read_text()
        )
        covered = set()
        for case in cases:
            response = self.api["paths"][case["path"]][case["method"]]["responses"][
                str(case["status"])
            ]
            media = (
                "application/problem+json"
                if case["status"] >= 400
                else "application/json"
            )
            name = response["content"][media]["schema"]["$ref"].split("/")[-1]
            covered.add(name)
            validator = Draft202012Validator(
                {"$defs": self.core["$defs"], "$ref": "#/$defs/" + name},
                format_checker=FormatChecker(formats=["uuid", "date-time"]),
            )
            with self.subTest(name=case["name"]):
                self.assertTrue(
                    validator.is_valid(case["data"]),
                    list(validator.iter_errors(case["data"])),
                )
                if case["status"] >= 400:
                    self.assertEqual(case["data"]["status"], case["status"])
        expected = set()
        for item in self.api["paths"].values():
            for op in item.values():
                for status, response in op["responses"].items():
                    json_body = response.get("content", {}).get("application/json")
                    if status.startswith("2") and json_body:
                        expected.add(json_body["schema"]["$ref"].split("/")[-1])
        self.assertTrue(expected <= covered, expected - covered)

    def test_strong_etag_values(self):
        op = self.api["paths"]["/issues/{id}/resolve"]["post"]
        schema = next(p["schema"] for p in op["parameters"] if p["name"] == "If-Match")
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid('"12"'))
        for value in ("*", 'W/"12"', "12", '"12"\n'):
            self.assertFalse(validator.is_valid(value))

    def test_quality_response_requires_exactly_five_gates(self):
        cases = json.loads(
            (ROOT / "docs/contracts/http_response_examples.json").read_text()
        )
        data = next(
            c["data"] for c in cases if c["path"] == "/productions/{id}/quality"
        )
        validator = Draft202012Validator(
            {"$defs": self.core["$defs"], "$ref": "#/$defs/QualitySnapshot"}
        )
        changed = copy.deepcopy(data)
        changed["gates"] = changed["gates"][:4]
        self.assertFalse(validator.is_valid(changed))
        changed = copy.deepcopy(data)
        changed["gates"] = [dict(data["gates"][0], status="pending") for _ in range(5)]
        self.assertFalse(validator.is_valid(changed))

    def test_project_boundary_mutations_really_fail(self):
        for mutate in (
            lambda api: api["paths"]["/tasks/{id}"]["get"].pop("security"),
            lambda api: api["paths"]["/issues/{id}/resolve"]["post"][
                "parameters"
            ].pop(),
            lambda api: api["paths"]["/reviews"]["post"].update(
                security=[{"WorkerToken": []}]
            ),
            lambda api: api["paths"]["/books"]["post"].update(
                security=[{"BrowserSession": []}]
            ),
            lambda api: api["components"]["schemas"].update(UUID={"type": "string"}),
            lambda api: api["components"]["schemas"].update(
                UUID={"$ref": "https://invalid.test/schema"}
            ),
        ):
            changed = copy.deepcopy(self.api)
            mutate(changed)
            self.assertTrue(audit(changed, self.core))
        self.assertEqual(audit(self.api, self.core), [])

    def test_invalid_spec_mutations_really_fail(self):
        for mutate in (
            lambda api: api.pop("info"),
            lambda api: api["paths"]["/tasks/{id}"]["get"]["parameters"].clear(),
            lambda api: api["paths"]["/tasks/{id}"]["get"]["responses"].update(
                {"wrong": {"description": "错误状态码"}}
            ),
        ):
            changed = copy.deepcopy(self.api)
            mutate(changed)
            self.assertTrue(
                list(
                    OpenAPIV31SpecValidator(
                        changed, base_uri=self.path.as_uri()
                    ).iter_errors()
                )
            )


if __name__ == "__main__":
    unittest.main()
