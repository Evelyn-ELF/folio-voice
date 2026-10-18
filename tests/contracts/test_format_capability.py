"""阻止缺少可选格式依赖时静默跳过验证。"""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "design_validator", ROOT / "tools/validate_design_contracts.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class FormatCapabilityTests(unittest.TestCase):
    def test_missing_date_time_capability_is_an_error(self):
        available = {
            k: v for k, v in FormatChecker.checkers.items() if k != "date-time"
        }
        with patch.dict(FormatChecker.checkers, available, clear=True):
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "格式校验能力缺失"):
                    VALIDATOR.main()


if __name__ == "__main__":
    unittest.main()
