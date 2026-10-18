"""本地与CI共用的工程检查；依赖由uv sync --locked与npm ci安装。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT_PATHS = [
    "apps/api",
    "workers",
    "packages",
    "tests",
    "scripts/check.py",
    "scripts/smoke_http.py",
    "scripts/check_container.py",
    "tools/generate_contract_types.py",
    "tools/validate_design_contracts.py",
    "tools/validate_http_contract.py",
    "tools/check_module_boundaries.py",
    "tools/test_generate_contract_types.py",
    "tools/test_check_documents.py",
    "tools/test_validate_http_contract.py",
]


def commands() -> list[list[str]]:
    python = sys.executable
    return [
        [python, "tools/check_documents.py"],
        [python, "tools/generate_contract_types.py", "--check"],
        [python, "tools/validate_design_contracts.py"],
        [python, "tools/validate_http_contract.py"],
        *[
            [python, "-m", "unittest", "discover", "-s", directory, "-p", "test_*.py"]
            for directory in [
                "tools",
                "tests/contracts",
                "tests/core",
                "tests/storage",
                "tests/engineering",
            ]
        ],
        [python, "-m", "ruff", "check", *LINT_PATHS],
        [
            python,
            "-m",
            "ruff",
            "format",
            "--check",
            "--exclude",
            "packages/contracts/generated.py",
            *LINT_PATHS,
        ],
        [python, "-m", "mypy"],
        [python, "tools/check_module_boundaries.py"],
        ["npm", "run", "check:contracts"],
        ["npm", "run", "check:boundaries"],
        ["npm", "run", "test:web"],
        ["npm", "run", "build:web"],
        [python, "scripts/smoke_http.py"],
    ]


def main() -> int:
    for command in commands():
        print("执行：" + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print("检查失败，后续检查未执行。", flush=True)
            return result.returncode
    print("适用工程检查通过；真实模型、音频、设备与远端CI未由此验证。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
