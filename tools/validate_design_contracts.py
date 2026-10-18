"""校验设计Schema及自写正反例；不验证产品运行行为。"""

import json
from importlib.metadata import version
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        format_checker = FormatChecker(formats=["uuid", "date-time"])
    except KeyError as exc:
        raise RuntimeError(
            "格式校验能力缺失，请安装docs/validation/契约校验环境.txt的全部依赖"
        ) from exc
    schema = json.loads((root / "docs/contracts/core.schema.json").read_text())
    examples = json.loads((root / "docs/contracts/examples.json").read_text())
    Draft202012Validator.check_schema(schema)
    records = []
    for group in ("valid", "invalid"):
        for example in examples[group]:
            scoped = dict(schema)
            scoped.pop("oneOf")
            scoped["$ref"] = "#/$defs/" + example["schema"]
            validator = Draft202012Validator(scoped, format_checker=format_checker)
            errors = list(validator.iter_errors(example["data"]))
            matched = (not errors) == (group == "valid")
            records.append(
                {
                    "样例": example["name"],
                    "预期": group,
                    "符合预期": matched,
                    "结构错误数": len(errors),
                }
            )
    result = {
        "范围": "Schema元校验及结构正反例，非产品测试",
        "校验器": "jsonschema " + version("jsonschema"),
        "Schema元校验": "通过",
        "样例": records,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(record["符合预期"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
