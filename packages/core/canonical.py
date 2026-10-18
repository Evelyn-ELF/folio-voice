"""fv-json-v1：RFC 8785的无浮点子集；完整契约校验由调用边界负责。"""

from __future__ import annotations

import hashlib
import json
from typing import cast

MAX_SAFE_INTEGER = 2**53 - 1


def canonical_json(value: object) -> bytes:
    """输出规范UTF-8；拒绝浮点、非JSON类型、孤立代理码点和循环。"""
    ancestors: set[int] = set()

    def encode(item: object) -> str:
        if item is None:
            return "null"
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) is int:
            if not -MAX_SAFE_INTEGER <= item <= MAX_SAFE_INTEGER:
                raise ValueError("整数超出跨语言安全范围")
            return str(item)
        if type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("字符串包含非法Unicode代理码点") from exc
            return json.dumps(item, ensure_ascii=False)
        if type(item) not in (list, dict):
            raise ValueError("规范配置只接受JSON值；小数必须使用规范十进制字符串")
        identity = id(item)
        if identity in ancestors:
            raise ValueError("规范配置不能包含循环引用")
        ancestors.add(identity)
        try:
            if isinstance(item, list):
                return "[" + ",".join(encode(child) for child in item) + "]"
            mapping = cast(dict[object, object], item)
            if any(type(key) is not str for key in mapping):
                raise ValueError("JSON对象键必须为字符串")
            strings = cast(dict[str, object], mapping)
            # 先验证所有键，保证排序时的代理码点错误也是领域错误。
            keys = {key: encode(key) for key in strings}
            ordered = sorted(strings, key=lambda key: key.encode("utf-16-be"))
            return (
                "{"
                + ",".join(keys[key] + ":" + encode(strings[key]) for key in ordered)
                + "}"
            )
        finally:
            ancestors.remove(identity)

    try:
        return encode(value).encode("utf-8")
    except RecursionError as exc:
        raise ValueError("规范配置嵌套过深") from exc


def configuration_hash(value: object) -> str:
    """对规范字节计算SHA-256；QualityPolicy仅传入经Schema校验的config。"""
    return hashlib.sha256(canonical_json(value)).hexdigest()


def parse_json(source: str) -> object:
    """保留解析前的重复键/数字错误，禁止先用宽松解析器丢失信息。"""

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("JSON对象包含重复键")
            result[key] = value
        return result

    def reject_number(token: str) -> object:
        raise ValueError("规范配置不接受浮点或非有限数值")

    try:
        value: object = json.loads(
            source,
            object_pairs_hook=pairs,
            parse_float=reject_number,
            parse_constant=reject_number,
        )
        canonical_json(value)
        return value
    except RecursionError as exc:
        raise ValueError("规范配置嵌套过深") from exc
