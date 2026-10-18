"""按产品目录静态检查Python依赖；不执行被检查代码。"""

import argparse
import ast
import json
import sys
from pathlib import Path

LAYERS = {
    "apps.api": ("packages.core", "packages.contracts", "packages.adapters"),
    "packages.core": ("packages.contracts",),
    "packages.contracts": (),
    "packages.adapters": ("packages.core", "packages.contracts"),
    "workers.container": ("packages.contracts", "packages.adapters.http_client"),
    "workers.macos": ("packages.contracts", "packages.adapters.http_client"),
}
EXTERNAL = {
    "apps.api": {"fastapi", "starlette", "uvicorn", "pydantic"},
    "packages.adapters": {"httpx"},
}
DATABASE = {"sqlite3", "sqlalchemy", "alembic"}


def under(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def audit(root: Path) -> tuple[int, list[str]]:
    errors: list[str] = []
    paths = sorted(
        p
        for directory in ("apps", "packages", "workers")
        for p in (root / directory).rglob("*.py")
        if "node_modules" not in p.parts
    )
    modules = {
        ".".join(p.relative_to(root).with_suffix("").parts).removesuffix(".__init__"): p
        for p in paths
    }
    graph: dict[str, set[str]] = {m: set() for m in modules}
    for module, path in modules.items():
        layer = next((name for name in LAYERS if under(module, name)), None)
        if layer is None:
            errors.append(f"{path.relative_to(root)}：未分配模块依赖规则")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(root)}：解析失败：{exc}")
            continue
        imports: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((name.name, node.lineno) for name in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parent = (
                        module.split(".")
                        if path.name == "__init__.py"
                        else module.split(".")[:-1]
                    )
                    if node.level > len(parent):
                        errors.append(f"{module}:{node.lineno}：相对依赖超出仓库")
                        continue
                    base = ".".join(
                        parent[: len(parent) - node.level + 1]
                        + ([base] if base else [])
                    )
                if base in modules or base.split(".")[0] not in {
                    "apps",
                    "packages",
                    "workers",
                }:
                    imports.append((base, node.lineno))
                    imports.extend(
                        (base + "." + name.name, node.lineno)
                        for name in node.names
                        if base + "." + name.name in modules
                    )
                else:
                    imports.extend(
                        (base + "." + name.name, node.lineno) for name in node.names
                    )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"__import__", "eval", "exec"}
            ):
                errors.append(f"{module}:{node.lineno}：禁止动态依赖或代码加载")
        for target, line in imports:
            top = target.split(".")[0]
            if top in {"importlib", "runpy"}:
                errors.append(f"{module}:{line}：禁止动态依赖加载器{target}")
            if top in DATABASE and layer != "packages.adapters":
                errors.append(
                    f"{module}:{line}：数据库依赖只能位于适配器，由应用组合调用"
                )
            if top in {"apps", "packages", "workers"}:
                if not any(under(target, prefix) for prefix in (layer, *LAYERS[layer])):
                    errors.append(f"{module}:{line}：禁止依赖{target}")
                if target in modules:
                    graph[module].add(target)
                elif not any(name.startswith(target + ".") for name in modules):
                    errors.append(f"{module}:{line}：内部依赖不存在：{target}")
            elif top not in sys.stdlib_module_names and top not in EXTERNAL.get(
                layer, set()
            ):
                errors.append(f"{module}:{line}：未允许的外部依赖{target}")
    visiting: list[str] = []
    done: set[str] = set()

    def visit(module: str) -> None:
        if module in visiting:
            errors.append(
                "循环依赖：" + " → ".join(visiting[visiting.index(module) :] + [module])
            )
            return
        if module in done:
            return
        visiting.append(module)
        for target in sorted(graph[module]):
            visit(target)
        visiting.pop()
        done.add(module)

    # 导入子模块也会执行祖先包的__init__.py，将隐含依赖纳入环检查。
    for module in graph:
        parts = module.split(".")
        graph[module].update(
            ".".join(parts[:i])
            for i in range(1, len(parts))
            if ".".join(parts[:i]) in modules
        )
    for module in sorted(graph):
        visit(module)
    if not paths:
        errors.append("未找到产品Python模块")
    return len(paths), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    count, errors = audit(args.root.resolve())
    print(json.dumps({"文件数": count, "错误": errors}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
