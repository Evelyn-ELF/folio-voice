"""用临时文档副本验证检查命令；不修改工作文档或运行产品。"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/check_documents.py"


class DocumentChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "docs", self.root / "docs")
        shutil.copytree(
            ROOT / "tools",
            self.root / "tools",
            ignore=shutil.ignore_patterns("__pycache__", "node_modules", "dist"),
        )
        for name in (
            "packages",
            "tests",
            "migrations",
            ".agents/skills",
            "apps",
            "workers",
            "scripts",
            "deploy",
            ".github",
        ):
            shutil.copytree(
                ROOT / name,
                self.root / name,
                ignore=shutil.ignore_patterns("__pycache__", "node_modules", "dist"),
            )
        for name in (
            "README.md",
            "AGENTS.md",
            "archive/README.md",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "uv.lock",
            ".python-version",
            ".node-version",
            ".dockerignore",
        ):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def edit(self, name, transform):
        path = self.root / name
        path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")

    def run_check(self, expected):
        self.assertTrue(SCRIPT.is_file(), "文档检查命令尚未实现")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_current_documents_pass_without_writing_report(self):
        path = self.root / "docs/validation/文档检查.json"
        before = path.read_bytes()
        self.run_check(0)
        self.assertEqual(path.read_bytes(), before)

    def test_broken_anchor_is_rejected(self):
        self.edit("README.md", lambda s: s + "\n[坏链接](docs/系统设计.md#missing)\n")
        self.assertIn("锚点", str(self.run_check(1)["错误"]))

    def test_duplicate_requirement_is_rejected(self):
        def duplicate(s):
            row = next(line for line in s.splitlines() if line.startswith("| R01 |"))
            return s.replace(row, row + "\n" + row, 1)

        self.edit("docs/系统设计.md", duplicate)
        self.assertIn("重复编号", str(self.run_check(1)["错误"]))

    def test_requirement_without_validation_is_rejected(self):
        self.edit("docs/系统设计.md", lambda s: s.replace("| V01 |", "| 待定 |", 1))
        self.assertIn("验证映射", str(self.run_check(1)["错误"]))

    def test_missing_case_is_rejected(self):
        self.edit(
            "docs/验证计划.md",
            lambda s: "\n".join(
                line for line in s.splitlines() if not line.startswith("| V07 |")
            ),
        )
        self.assertIn("V07", str(self.run_check(1)["错误"]))

    def test_new_requirement_and_case_can_be_added(self):
        def rows(name, prefix):
            text = (self.root / name).read_text(encoding="utf-8")
            return re.findall(r"^\| " + prefix + r"\d+ \|.*$", text, re.M)

        requirements = rows("docs/系统设计.md", "R")
        cases = rows("docs/验证计划.md", "V")
        requirement = f"R{len(requirements) + 1:02}"
        case = f"V{len(cases) + 1:02}"
        for name, last, new in (
            (
                "docs/系统设计.md",
                requirements[-1],
                f"| {requirement} | 自写需求 | [范围](#scope) | {case} |",
            ),
            ("docs/验证计划.md", cases[-1], f"| {case} | {requirement} | 自写验收 |"),
        ):
            self.edit(
                name, lambda s, old=last, row=new: s.replace(old, old + "\n" + row, 1)
            )
        self.run_check(0)

    def test_archives_and_fenced_examples_are_not_scanned(self):
        (self.root / "archive/坏文档.md").write_text("[无效](missing.md) R999")
        self.edit("README.md", lambda s: s + "\n```md\n[示例](missing.md) R999\n```\n")
        self.run_check(0)

    def test_skipped_heading_level_is_rejected(self):
        self.edit("README.md", lambda s: s + "\n#### 跳级标题\n")
        self.assertIn("标题跳级", str(self.run_check(1)["错误"]))

    def test_extra_normative_document_is_rejected(self):
        (self.root / "docs/另一套规范.md").write_text("# 另一套规则\n")
        self.assertIn("活动文档集合", str(self.run_check(1)["错误"]))


if __name__ == "__main__":
    unittest.main()
