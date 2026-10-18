"""从本项目Schema子集生成静态类型；运行约束始终由原Schema校验。"""

from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import re
from collections.abc import Sequence
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
# 下列验证关键字不改变静态字段形状，完整语义仍保留在源Schema。
CONSTRAINTS = {
    "title",
    "description",
    "format",
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "default",
    "examples",
    "$comment",
}
SHAPES = {"$ref", "type", "const", "enum", "anyOf", "oneOf", "items"}
RESERVED = {
    "Literal",
    "NotRequired",
    "TypedDict",
    "SCHEMA_SHA256",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "string",
    "number",
    "boolean",
    "null",
    "any",
    "unknown",
    "never",
    "interface",
    "type",
    "export",
    "declare",
    "namespace",
}


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("契约节点必须为字符串键对象")
    return cast(dict[str, object], value)


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("契约节点必须为数组")
    return cast(list[object], value)


def _name(value: str, *, definition: bool = False) -> str:
    if (
        not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value)
        or keyword.iskeyword(value)
        or (definition and value in RESERVED)
    ):
        raise ValueError(f"暂不支持的类型或字段名称：{value}")
    return value


def _literal(value: object, language: str) -> str:
    if value is None:
        return "None" if language == "python" else "null"
    if not isinstance(value, (str, bool, int)):
        raise ValueError("静态常量只支持字符串、布尔值、整数或null")
    return (
        repr(value) if language == "python" else json.dumps(value, ensure_ascii=False)
    )


def _expression(node: dict[str, object], language: str, names: set[str]) -> str:
    unsupported = node.keys() - SHAPES - CONSTRAINTS
    if unsupported:
        raise ValueError(f"暂不支持的类型构造：{sorted(unsupported)}")
    if "$ref" in node:
        reference = node["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            raise ValueError("类型引用只支持本地$defs")
        target = reference.removeprefix("#/$defs/")
        if target not in names:
            raise ValueError(f"类型引用不存在：{target}")
        return target
    if "const" in node or "enum" in node:
        values = [node["const"]] if "const" in node else _sequence(node["enum"])
        if not values:
            raise ValueError("静态枚举不能为空")
        literals = [_literal(value, language) for value in values]
        return (
            f"Literal[{', '.join(literals)}]"
            if language == "python"
            else " | ".join(literals)
        )
    for union in ("anyOf", "oneOf"):
        if union in node:
            options = _sequence(node[union])
            if not options:
                raise ValueError("静态联合类型不能为空")
            return " | ".join(
                _expression(_mapping(item), language, names) for item in options
            )
    primitives = {
        "string": ("str", "string"),
        "integer": ("int", "number"),
        "number": ("float", "number"),
        "boolean": ("bool", "boolean"),
        "null": ("None", "null"),
    }
    kind = node.get("type")
    if isinstance(kind, str) and kind in primitives:
        return primitives[kind][language == "typescript"]
    if kind == "array":
        item_type = _expression(_mapping(node.get("items")), language, names)
        return f"list[{item_type}]" if language == "python" else f"Array<{item_type}>"
    raise ValueError(f"暂不支持的静态类型：{kind}")


def _ordered_definitions(definitions: dict[str, object]) -> list[str]:
    """先生成被引用类型；递归形状明确拒绝，避免输出不能导入的Python。"""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in ordered:
            return
        if name in visiting:
            raise ValueError(f"暂不支持递归类型：{name}")
        if name not in definitions:
            raise ValueError(f"类型引用不存在：{name}")
        visiting.add(name)

        def references(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "$ref":
                        if not isinstance(value, str) or not value.startswith(
                            "#/$defs/"
                        ):
                            raise ValueError("类型引用只支持本地$defs")
                        visit(value.removeprefix("#/$defs/"))
                    else:
                        references(value)
            elif isinstance(node, list):
                for value in node:
                    references(value)

        references(definitions[name])
        visiting.remove(name)
        ordered.append(name)

    for name in definitions:
        _name(name, definition=True)
        visit(name)
    return ordered


def generate(schema_bytes: bytes) -> dict[str, str]:
    """返回两个生成文件的完整内容；失败时不写入任何文件。"""
    schema = _mapping(json.loads(schema_bytes))
    definitions = _mapping(schema.get("$defs"))
    if not definitions:
        raise ValueError("源契约缺少非空$defs")
    names = set(definitions)
    python: list[str] = []
    typescript: list[str] = []
    for name in _ordered_definitions(definitions):
        node = _mapping(definitions[name])
        if node.get("type") != "object":
            python.append(f"type {name} = {_expression(node, 'python', names)}\n")
            typescript.append(
                f"export type {name} = {_expression(node, 'typescript', names)};\n"
            )
            continue
        unsupported = (
            node.keys()
            - CONSTRAINTS
            - {
                "type",
                "properties",
                "required",
                "additionalProperties",
                "allOf",
            }
        )
        if unsupported or node.get("additionalProperties") is not False:
            raise ValueError(f"对象{name}包含不支持的构造或未拒绝未知字段")
        properties = _mapping(node.get("properties"))
        required = set(_sequence(node.get("required", [])))
        if not required.issubset(properties):
            raise ValueError(f"对象{name}的必填字段没有定义")
        python.append(f"class {name}(TypedDict):")
        typescript.append(f"export type {name} = {{")
        for field, raw_type in properties.items():
            _name(field)
            field_schema = _mapping(raw_type)
            py_type = _expression(field_schema, "python", names)
            ts_type = _expression(field_schema, "typescript", names)
            optional = field not in required
            if optional:
                py_type = f"NotRequired[{py_type}]"
            python.append(f"    {field}: {py_type}")
            typescript.append(
                f"  {json.dumps(field)}{'?' if optional else ''}: {ts_type};"
            )
        if not properties:
            python.append("    pass")
        python.append("")
        typescript.append("};\n")
    digest = hashlib.sha256(schema_bytes).hexdigest()
    imports = [
        name
        for name in ("Literal", "NotRequired", "TypedDict")
        if any(name in line for line in python)
    ]
    py_header = (
        '"""自动生成，请勿手改；运行约束、条件与权限须另按源Schema及服务规则验证。"""\n\n'
        + (f"from typing import {', '.join(imports)}\n\n" if imports else "")
        + f'SCHEMA_SHA256 = "{digest}"\n\n'
    )
    ts_header = (
        "// 自动生成，请勿手改；运行约束、条件与权限须另按源Schema及服务规则验证。\n"
        + f'export const SCHEMA_SHA256 = "{digest}";\n\n'
    )
    return {
        "generated.py": py_header + "\n".join(python).rstrip() + "\n",
        "generated.ts": ts_header + "\n".join(typescript).rstrip() + "\n",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成核心契约类型，或只读检查生成物是否过期"
    )
    parser.add_argument(
        "--schema", type=Path, default=ROOT / "docs/contracts/core.schema.json"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "packages/contracts")
    parser.add_argument("--check", action="store_true", help="只检查，不写入")
    args = parser.parse_args(argv)
    try:
        outputs = generate(args.schema.read_bytes())
        stale: list[str] = []
        for name, content in outputs.items():
            target = args.output_dir / name
            if args.check:
                if not target.is_file() or target.read_bytes() != content.encode(
                    "utf-8"
                ):
                    stale.append(name)
            else:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
        if stale:
            print("生成物缺失或过期：" + "、".join(stale))
            return 1
    except (OSError, ValueError, TypeError) as exc:
        print(f"类型生成失败：{exc}")
        return 2
    print("生成物一致" if args.check else "核心契约类型已生成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
