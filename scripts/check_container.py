"""验证已构建镜像；仅使用临时容器与自写测试，结束回收本次容器。"""

import argparse
import json
import subprocess
import time
import tomllib
from pathlib import Path
from uuid import uuid4

from scripts.smoke_http import fetch, verify_http

ROOT = Path(__file__).resolve().parents[1]


def command(args: list[str]) -> str:
    result = subprocess.run(
        args, text=True, capture_output=True, timeout=40, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"{args!r}退出{result.returncode}：{result.stdout}{result.stderr}"
        )
    return result.stdout + result.stderr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="folio-voice:development")
    image = parser.parse_args().image
    name = "folio-check-" + uuid4().hex
    record: dict[str, object] = {"镜像": image, "临时容器": name}
    print(json.dumps(record, ensure_ascii=False), flush=True)
    create = [
        "docker",
        "create",
        "--pull=never",
        "--name",
        name,
        "--label",
        "io.folio-voice.check=" + name,
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--publish",
        "127.0.0.1::8000",
    ]
    for directory in ["migrations", "tests"]:
        create += [
            "--mount",
            f"type=bind,src={ROOT / directory},dst=/app/{directory},readonly",
        ]
    container = command([*create, image]).strip()
    try:
        command(["docker", "start", container])
        address = command(["docker", "port", container, "8000/tcp"]).strip()
        if not address.startswith("127.0.0.1:") or "\n" in address:
            raise RuntimeError("临时容器没有仅绑定回环地址")
        base = "http://" + address
        deadline = time.monotonic() + 15
        while True:
            try:
                if fetch(base, "/api/v1/health/live")[0] == 200:
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError(command(["docker", "logs", container]))
            time.sleep(0.1)
        # 与本机冒烟使用同一检查函数，不维护两套HTTP预期。
        record["HTTP"] = verify_http(base)
        environment = command(
            [
                "docker",
                "exec",
                container,
                "python",
                "-c",
                'import json,os,sys,sqlite3,importlib.metadata as m; print(json.dumps({"Python":sys.version.split()[0],"UID":os.geteuid(),"SQLite":sqlite3.sqlite_version,"包":{d.metadata["Name"]:d.version for d in m.distributions()}}))',
            ]
        )
        runtime = json.loads(environment)
        if runtime["UID"] != 10001:
            raise RuntimeError("应用未以预期非root用户运行")
        if runtime["Python"] != (ROOT / ".python-version").read_text().strip():
            raise RuntimeError("运行Python偏离固定版本")
        locked = {
            p["name"]: p["version"]
            for p in tomllib.loads((ROOT / "uv.lock").read_text())["package"]
        }
        installed = {
            name.lower().replace("_", "-"): version
            for name, version in runtime["包"].items()
        }
        if any(locked.get(name) != version for name, version in installed.items()):
            raise RuntimeError("容器依赖偏离uv.lock")
        for dependency in tomllib.loads((ROOT / "pyproject.toml").read_text())[
            "project"
        ]["dependencies"]:
            name, version = dependency.split("==")
            if installed.get(name) != version:
                raise RuntimeError("容器缺少固定运行依赖")
        record["运行环境"] = runtime
        record["存储回归"] = command(
            [
                "docker",
                "exec",
                container,
                "python",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/storage",
                "-p",
                "test_*.py",
            ]
        )
        for worker in ["container", "macos"]:
            diagnose = json.loads(
                command(
                    [
                        "docker",
                        "exec",
                        container,
                        "python",
                        "-m",
                        f"workers.{worker}.main",
                        "--diagnose",
                    ]
                )
            )
            if diagnose["就绪"] or diagnose["能力"]:
                raise RuntimeError("未实现执行器虚报能力")
            record[worker + "诊断"] = diagnose
        record["镜像ID"] = command(
            ["docker", "inspect", "--format", "{{.Image}}", container]
        ).strip()
        record["结果"] = "通过；不代表业务、模型或设备验收"
    finally:
        command(["docker", "rm", "--force", container])
        record["容器回收"] = "完成"
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
