FROM registry-1.docker.io/library/node:26.4.0-bookworm-slim@sha256:ec82d089a8ae2cf02628da7b34ea57dc357b24db724d557fe2d240e6beb659c1 AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY apps/web ./apps/web
COPY packages/contracts/generated.ts ./packages/contracts/generated.ts
RUN npm run build:web

FROM registry-1.docker.io/library/python:3.14.2-slim-bookworm@sha256:e87711ef5c86aaeaa7031718a69db79d334d94c545c709583f651b8185870941 AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN python -m pip install --no-cache-dir uv==0.11.25
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python && uv cache clean
COPY apps/api ./apps/api
COPY packages ./packages
COPY workers ./workers
COPY --from=web /app/apps/web/dist ./apps/web/dist
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
