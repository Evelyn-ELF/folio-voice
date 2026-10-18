"""F03应用入口：只有存活检查，业务及认证由F04实现。"""

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from packages.contracts.generated import HealthLive, ProblemDetails


def create_app() -> FastAPI:
    app = FastAPI(title="Folio Voice", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(HTTPException)
    async def problem(request: Request, exc: HTTPException) -> JSONResponse:
        body: ProblemDetails = {
            "type": "about:blank",
            "title": "请求未完成",
            "status": exc.status_code,
            "detail": "认证服务尚未实现。"
            if exc.status_code == 401
            else "接口尚未实现或资源不存在。",
            "instance": request.url.path,
            "code": "AUTH_REQUIRED" if exc.status_code == 401 else "NOT_FOUND",
            "request_id": str(uuid4()),
            "retryable": False,
            "affected_scope": [],
        }
        return JSONResponse(
            body, status_code=exc.status_code, media_type="application/problem+json"
        )

    @app.get("/api/v1/health/live")
    async def live() -> HealthLive:
        return {"status": "alive"}

    @app.get("/api/v1/health/ready")
    async def ready() -> None:
        raise HTTPException(status_code=401)

    @app.api_route(
        "/api/v1/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def unavailable(path: str) -> None:
        raise HTTPException(status_code=404)

    web = Path(__file__).resolve().parents[1] / "web/dist"
    if web.is_dir():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app


app = create_app()
