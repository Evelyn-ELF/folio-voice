"""启动独立Uvicorn进程，检查真实回环HTTP与构建页面，结束后回收进程。"""

import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(base: str, path: str) -> tuple[int, str, bytes]:
    try:
        response = urllib.request.urlopen(base + path, timeout=1)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers.get_content_type(), response.read()


def verify_http(base: str) -> dict[str, int | str]:
    status, media, body = fetch(base, "/api/v1/health/live")
    assert status == 200 and json.loads(body) == {"status": "alive"}
    status, media, body = fetch(base, "/api/v1/health/ready")
    assert status == 401 and media == "application/problem+json"
    status, media, body = fetch(base, "/")
    assert status == 200 and media == "text/html" and b"zh-CN" in body
    asset = re.search(r'src="([^"]+\.js)"', body.decode())
    assert asset is not None
    assert fetch(base, asset[1])[0] == 200
    for path in [
        "/api/v1/productions",
        "/.env",
        "/pyproject.toml",
        "/openapi.json",
    ]:
        assert fetch(base, path)[0] == 404, path
    return {
        "存活": 200,
        "未认证就绪": 401,
        "中文页面": 200,
        "静态资源": 200,
        "未实现接口与私有路径": 404,
        "说明": "真实HTTP；未验证产品任务、浏览器交互或模型",
    }


def main() -> None:
    with socket.socket() as listener, tempfile.TemporaryFile() as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--fd",
                str(listener.fileno()),
            ],
            cwd=ROOT,
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=log,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 10
            while True:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read().decode())
                try:
                    if fetch(base, "/api/v1/health/live")[0] == 200:
                        break
                except (OSError, urllib.error.URLError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("应用启动超时")
                time.sleep(0.05)
            print(json.dumps(verify_http(base), ensure_ascii=False))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
