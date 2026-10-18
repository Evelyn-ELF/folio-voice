"""离线校验OpenAPI、核心引用、请求样例和本项目HTTP边界。"""

import argparse
import json
from importlib.metadata import version
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from openapi_spec_validator import OpenAPIV31SpecValidator

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"get", "post", "put", "delete"}


def audit(spec: dict, core: dict) -> list[str]:
    """标准结构之外的项目边界；服务仍须执行身份和业务检查。"""
    errors = []

    def references(node: object, prefixes: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("$ref", "$dynamicRef", "$recursiveRef"):
                    if not isinstance(value, str) or not value.startswith(prefixes):
                        errors.append("OpenAPI引用必须在本地契约集合内")
                else:
                    references(value, prefixes)
        elif isinstance(node, list):
            for child in node:
                references(child, prefixes)

    references(spec, ("#/components/", "core.schema.json#/$defs/"))
    references(core, ("#/$defs/",))
    for name, value in spec.get("components", {}).get("schemas", {}).items():
        if (
            value != {"$ref": f"core.schema.json#/$defs/{name}"}
            or name not in core["$defs"]
        ):
            errors.append(f"{name}没有唯一引用核心结构")
    for path, item in spec.get("paths", {}).items():
        for method, operation in item.items():
            if method not in METHODS:
                continue
            label = method + " " + path
            security = operation.get("security")
            if security is None or (
                not security and path not in ("/sessions", "/health/live")
            ):
                errors.append(label + "缺少显式认证")
            for alternative in security or []:
                if (
                    method != "get"
                    and "BrowserSession" in alternative
                    and "CsrfToken" not in alternative
                ):
                    errors.append(label + "缺少会话写入CSRF")
                if (
                    operation.get("x-actor-kind") == "human"
                    and "WorkerToken" in alternative
                ):
                    errors.append(label + "允许执行器冒充用户")
                if operation.get("x-session-only") and set(alternative) != {
                    "BrowserSession",
                    "CsrfToken",
                }:
                    errors.append(label + "人工操作必须仅使用用户会话")
            if operation.get("x-concurrency") == "etag":
                if not any(
                    p.get("name") == "If-Match" and p.get("required")
                    for p in operation.get("parameters", [])
                ):
                    errors.append(label + "缺少必需If-Match")
                if not {"409", "412"} <= operation.get("responses", {}).keys():
                    errors.append(label + "缺少版本/业务冲突响应")
            for code, response in operation.get("responses", {}).items():
                if (
                    code.isdigit()
                    and int(code) >= 400
                    and "application/problem+json" not in response.get("content", {})
                ):
                    errors.append(label + "错误响应不符合Problem Details")
            body = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json")
            )
            if method != "get" and body and path != "/tasks/{id}/heartbeat":
                name = body["schema"]["$ref"].split("/")[-1]
                definition = core["$defs"].get(name, {})
                if "request_id" not in definition.get("required", []):
                    errors.append(label + "缺少幂等request_id")
    return errors


def validate(root: Path) -> dict:
    path = (root / "docs/contracts/openapi.json").resolve()
    spec = json.loads(path.read_text())
    core = json.loads((path.parent / "core.schema.json").read_text())
    errors = audit(spec, core)
    if errors:
        raise ValueError("；".join(errors))
    standard = list(OpenAPIV31SpecValidator(spec, base_uri=path.as_uri()).iter_errors())
    if standard:
        raise ValueError("OpenAPI标准校验失败：" + str(standard[0]))
    checker = FormatChecker(formats=["uuid", "date-time"])
    examples = json.loads((path.parent / "http_examples.json").read_text())
    for case in examples:
        scoped = {"$defs": core["$defs"], "$ref": "#/$defs/" + case["schema"]}
        validator = Draft202012Validator(scoped, format_checker=checker)
        validator.validate(case["data"])
    responses = json.loads((path.parent / "http_response_examples.json").read_text())
    for case in responses:
        response = spec["paths"][case["path"]][case["method"]]["responses"][
            str(case["status"])
        ]
        media = (
            "application/problem+json" if case["status"] >= 400 else "application/json"
        )
        name = response["content"][media]["schema"]["$ref"].split("/")[-1]
        scoped = {"$defs": core["$defs"], "$ref": "#/$defs/" + name}
        Draft202012Validator(scoped, format_checker=checker).validate(case["data"])
        if case["status"] >= 400 and case["data"]["status"] != case["status"]:
            raise ValueError("Problem Details状态与HTTP响应不一致")
    return {
        "范围": "OpenAPI 3.1.1、离线引用、请求结构与协议边界，非服务测试",
        "校验器": "openapi-spec-validator " + version("openapi-spec-validator"),
        "操作数": sum(
            method in METHODS for item in spec["paths"].values() for method in item
        ),
        "请求样例数": len(examples),
        "响应样例数": len(responses),
        "结果": "通过",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="离线校验本项目HTTP机器契约")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = validate(args.root)
    except (ValueError, OSError, KeyError, ValidationError) as exc:
        print(
            json.dumps({"结果": "失败", "错误": str(exc)}, ensure_ascii=False, indent=2)
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
