"""通过真实CLI验证架构检查不会静默放行越层和循环。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BoundaryTests(unittest.TestCase):
    def check_tree(self, files, expected):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/check_module_boundaries.py"),
                    "--root",
                    directory,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            return json.loads(result.stdout)

    def test_core_and_adapter_direction(self):
        self.check_tree(
            {
                "packages/core/a.py": "from typing import Any",
                "packages/adapters/b.py": "from packages.core import a",
            },
            0,
        )

    def test_core_framework_and_database_are_rejected(self):
        for source in ("import fastapi", "import sqlite3", "from apps.api import main"):
            self.assertIn(
                "依赖", str(self.check_tree({"packages/core/a.py": source}, 1))
            )

    def test_worker_database_and_application_access_are_rejected(self):
        for source in (
            "import sqlite3",
            "from packages.adapters import sqlite_migrations",
            "from apps.api import main",
        ):
            self.check_tree({"workers/macos/a.py": source}, 1)

    def test_namespace_parent_does_not_bypass_worker_allowlist(self):
        for source in ("import packages.adapters", "from packages import adapters"):
            self.check_tree(
                {"workers/macos/a.py": source, "packages/adapters/http_client.py": ""},
                1,
            )

    def test_relative_import_cannot_bypass_boundary(self):
        self.check_tree(
            {
                "packages/core/a.py": "from ..adapters import b",
                "packages/adapters/b.py": "",
            },
            1,
        )

    def test_cycle_in_allowed_layer_is_rejected(self):
        result = self.check_tree(
            {
                "packages/core/a.py": "from . import b",
                "packages/core/b.py": "from . import a",
            },
            1,
        )
        self.assertIn("循环", str(result))

    def test_dynamic_import_and_unknown_module_are_rejected(self):
        for source in (
            'from importlib import import_module\nimport_module("sqlite3")',
            '__import__("sqlite3")',
            "import packages.core.missing",
        ):
            self.check_tree({"packages/core/a.py": source}, 1)

    def test_unassigned_product_module_is_rejected(self):
        self.check_tree({"packages/unknown/a.py": ""}, 1)

    def test_syntax_failure_is_reported(self):
        self.check_tree({"apps/api/a.py": "if"}, 1)
