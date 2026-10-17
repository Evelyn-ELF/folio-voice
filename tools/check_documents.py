"""检查项目约定的活动Markdown；仅用标准库，不联网、不判断自然语言语义。"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


DOCUMENTS = ("系统设计.md", "工程规范.md", "验证计划.md", "开发任务.md")
OWNERS = {
    **dict.fromkeys(("R", "INV", "ADR", "K", "Q", "D"), "系统设计.md"),
    **dict.fromkeys(("V", "E", "C"), "验证计划.md"),
    **dict.fromkeys(("F", "I", "A"), "开发任务.md"),
    **dict.fromkeys(("S", "N", "T"), "工程规范.md"),
}
ID = r"(?:INV|ADR|R|K|Q|D|V|E|C|F|I|A|S|N|T)\d{1,3}"
REFERENCE = re.compile(r"(?<![A-Za-z0-9_])(" + ID + r")(?![A-Za-z0-9_])")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
ANCHOR = re.compile(r'<a id="([^"]+)"></a>')


def prose(text: str) -> tuple[str, bool]:
    """围栏中的示例不参与结构、链接及编号检查，保留原行号。"""
    fence = None
    output = []
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if marker and fence is None:
            fence = marker[1]
            output.append("")
        elif (marker and fence and marker[1][0] == fence[0]
              and len(marker[1]) >= len(fence) and not marker[2].strip()):
            fence = None
            output.append("")
        else:
            output.append("" if fence else line)
    return "\n".join(output) + "\n", fence is not None


def identifiers(text: str) -> set[str]:
    result = set(REFERENCE.findall(text))
    for match in re.finditer(r"(" + ID + r")[–—-](" + ID + r")", text):
        left, right = [re.fullmatch(r"([A-Z]+)(\d+)", x) for x in match.groups()]
        if left[1] == right[1]:
            for number in range(int(left[2]), int(right[2]) + 1):
                result.add(left[1] + str(number).zfill(len(left[2])))
    return result


def inspect_structure(name: str, text: str, errors: list[str]) -> None:
    previous = 0
    numbers: dict[tuple[int, ...], list[int]] = {}
    current: tuple[int, ...] = ()
    anchors = ANCHOR.findall(text)
    if len(anchors) != len(set(anchors)):
        errors.append(f"{name}: 重复锚点")
    for line in text.splitlines():
        heading = re.match(r"^(#{1,6}) (.+)", line)
        if heading:
            level = len(heading[1])
            if previous and level > previous + 1:
                errors.append(f"{name}: 标题跳级 {line}")
            previous = level
            numbered = re.match(r"(\d+(?:\.\d+)*)\.? ", heading[2])
            if numbered:
                path = tuple(map(int, numbered[1].split(".")))
                wrong_parent = len(path) > 1 and path[:-1] != current[:len(path) - 1]
                if len(path) != level - 1 or wrong_parent:
                    errors.append(f"{name}: 章节归属不符 {line}")
                numbers.setdefault(path[:-1], []).append(path[-1])
                current = path
    for parent, items in numbers.items():
        if items != list(range(1, len(items) + 1)):
            errors.append(f"{name}: 章节编号不连续或重复 {parent}: {items}")
    for match in re.finditer(r"(?:^\|.*\n)+", text, re.M):
        rows = match[0].splitlines()
        if len(rows) < 2 or not re.fullmatch(r"[| :\-]+", rows[1]):
            errors.append(f"{name}: 表格缺少表头或分隔行 {rows[0][:50]}")
        elif len({len(re.split(r"(?<!\\)\|", row)) for row in rows}) != 1:
            errors.append(f"{name}: 表格列数不一致 {rows[0][:50]}")


def check(root: Path) -> dict:
    errors: list[str] = []
    paths = [Path("README.md"), Path("AGENTS.md")]
    paths += [Path("docs") / name for name in DOCUMENTS]
    actual = {p.name for p in (root / "docs").glob("*.md")}
    if actual != set(DOCUMENTS):
        errors.append("活动文档集合与四份入口约定不符: " + str(sorted(actual)))
    texts = {}
    hashes = {}
    for path in paths:
        try:
            raw = (root / path).read_bytes()
            text, unclosed = prose(raw.decode("utf-8"))
        except (OSError, UnicodeError) as exc:
            errors.append(f"{path}: 无法读取 {exc}")
            continue
        texts[path] = text
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        if unclosed:
            errors.append(f"{path}: 代码围栏未关闭")
        inspect_structure(str(path), text, errors)

    links = 0
    for path, text in texts.items():
        for destination in LINK.findall(text):
            url = urlsplit(destination)
            if url.scheme or url.netloc:
                continue
            links += 1
            target = root / path
            if url.path:
                target = (root / path.parent / unquote(url.path)).resolve()
            if not target.is_file():
                errors.append(f"{path}: 本地链接文件不存在 {destination}")
            elif url.fragment:
                if target.suffix != ".md":
                    errors.append(f"{path}: 非Markdown附件不支持章节锚点 {destination}")
                    continue
                target_text, _ = prose(target.read_text(encoding="utf-8"))
                if unquote(url.fragment) not in ANCHOR.findall(target_text):
                    errors.append(f"{path}: 本地链接锚点不存在 {destination}")

    definitions: dict[str, list[str]] = {}
    requirement_cases = {}
    case_requirements = {}
    for path, text in texts.items():
        for line in text.splitlines():
            table_id = re.match(r"^\| (" + ID + r")(?=\s)", line)
            heading_id = re.match(r"^### \d+\.\d+ ([EF]\d{2,3})：", line)
            match = table_id or heading_id
            if match:
                item = match[1]
                prefix = re.match(r"[A-Z]+", item)[0]
                if path.name != OWNERS[prefix]:
                    errors.append(f"{path}: 编号{item}应在{OWNERS[prefix]}定义")
                definitions.setdefault(item, []).append(str(path))
                cells = re.split(r"(?<!\\)\|", line)
                if prefix == "R":
                    requirement_cases[item] = identifiers(cells[-2]) if len(cells) >= 6 else set()
                elif prefix == "V":
                    case_requirements[item] = identifiers(cells[2]) if len(cells) >= 5 else set()

    for item, locations in definitions.items():
        if len(locations) != 1:
            errors.append(f"重复编号 {item}: {locations}")
    counts = Counter(re.match(r"[A-Z]+", item)[0] for item in definitions)
    for prefix in OWNERS:
        numbers = sorted(
            int(item[len(prefix):]) for item in definitions
            if re.fullmatch(prefix + r"\d+", item)
        )
        first = 0 if prefix == "I" else 1
        if not numbers or numbers != list(range(first, max(numbers) + 1)):
            errors.append(f"{prefix}编号缺失或不连续: {numbers}")
    for path, text in texts.items():
        unknown = identifiers(text) - definitions.keys()
        if unknown:
            errors.append(f"{path}: 未定义编号 {', '.join(sorted(unknown))}")
    forward = {
        (r, v) for r, values in requirement_cases.items()
        for v in values if v.startswith("V")
    }
    backward = {
        (r, v) for v, values in case_requirements.items()
        for r in values if re.fullmatch(r"R\d+", r)
    }
    if (forward != backward or set(requirement_cases) != {r for r, _ in forward}
            or set(case_requirements) != {v for _, v in backward}):
        errors.append("需求与验证映射缺失或双向不一致")
    return {
        "检查时间UTC": datetime.now(timezone.utc).isoformat(),
        "范围": "活动文档结构、显式锚点、内联本地链接、编号归属及R/V双向映射",
        "边界": "不检查归档、外部网页、自然语言冲突或Schema业务语义",
        "输入SHA256": hashes,
        "本地链接数": links,
        "定义编号数": dict(sorted(counts.items())),
        "错误": errors,
        "结果": "失败" if errors else "通过",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="仓库根目录；默认按脚本位置确定")
    parser.add_argument("--output", type=Path, help="显式指定JSON结果文件；默认只输出、不写文件")
    args = parser.parse_args()
    result = check(args.root.resolve())
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 1 if result["错误"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
