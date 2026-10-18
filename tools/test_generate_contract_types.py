"""类型生成的行为测试；过期检查必须只读，未知结构不得退化为any。"""

import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools/generate_contract_types.py"


class ContractTypeGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schema = self.root / "core.schema.json"
        self.output = self.root / "types"
        self.document = {
            "$defs": {
                "ID": {"type": "string"},
                "Request": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"$ref": "#/$defs/ID"},
                        "version": {"const": 2},
                        "mode": {"enum": ["执行", "停止"]},
                        "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "items": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["id", "version", "mode", "items"],
                },
            }
        }
        self.save_schema()

    def save_schema(self):
        self.schema.write_text(
            json.dumps(self.document, ensure_ascii=False), encoding="utf-8"
        )

    def command(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--schema",
                str(self.schema),
                "--output-dir",
                str(self.output),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_generated(self):
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_python_can_be_imported_with_required_and_optional_fields(self):
        self.assert_generated()
        namespace = runpy.run_path(str(self.output / "generated.py"))
        request = namespace["Request"]
        self.assertEqual(request.__required_keys__, {"id", "version", "mode", "items"})
        self.assertEqual(request.__optional_keys__, {"note"})
        self.assertEqual(
            request(id="测试", version=2, mode="执行", items=[1])["items"], [1]
        )
        typescript = (self.output / "generated.ts").read_text()
        self.assertIn('"note"?: string | null;', typescript)
        self.assertIn('"mode": "执行" | "停止";', typescript)
        self.assertIn('"version": 2;', typescript)
        self.assertIn('"items": Array<number>;', typescript)

    def test_identical_source_produces_identical_bytes(self):
        self.assert_generated()
        first = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.assert_generated()
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertEqual(self.command("--check").returncode, 0)

    def test_check_missing_files_does_not_create_output_directory(self):
        result = self.command("--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())

    def test_check_detects_manual_changes_and_does_not_repair_them(self):
        self.assert_generated()
        generated = self.output / "generated.py"
        generated.write_text("# 手工写坏的生成物\n")
        result = self.command("--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(generated.read_text(), "# 手工写坏的生成物\n")

    def test_source_change_invalidates_both_outputs_even_when_only_constraint_changes(
        self,
    ):
        self.assert_generated()
        original = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.document["$defs"]["ID"]["minLength"] = 1
        self.save_schema()
        result = self.command("--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("generated.py", result.stdout)
        self.assertIn("generated.ts", result.stdout)
        self.assertEqual(
            original, {p.name: p.read_bytes() for p in self.output.iterdir()}
        )

    def test_unsupported_type_dangling_reference_and_unsafe_name_fail_without_writing(
        self,
    ):
        bad_definitions = [
            {"value": {}},
            {"value": {"type": "object", "additionalProperties": True}},
            {"value": {"$ref": "https://example.invalid/schema"}},
            {"value": {"$ref": "#/$defs/Missing"}},
            {"injected; code": {"type": "string"}},
            {"class": {"type": "string"}},
            {"value": {"type": "string", "newUnknownKeyword": True}},
        ]
        for definitions in bad_definitions:
            with self.subTest(definitions=definitions):
                self.document["$defs"] = definitions
                self.save_schema()
                result = self.command()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.output.exists())

    def test_current_core_schema_can_be_generated_and_imported(self):
        self.schema.write_bytes((ROOT / "docs/contracts/core.schema.json").read_bytes())
        self.assert_generated()
        namespace = runpy.run_path(str(self.output / "generated.py"))
        self.assertEqual(
            namespace["ReleaseCommand"].__required_keys__,
            {
                "request_id",
                "artifact_id",
                "artifact_sha256",
                "deliverable_kind",
                "quality_revision",
                "contract_version",
            },
        )
        self.assertIn("input_snapshot_sha256", namespace["Heartbeat"].__required_keys__)


if __name__ == "__main__":
    unittest.main()
