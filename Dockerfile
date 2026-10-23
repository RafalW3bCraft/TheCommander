FROM docker.io/library/node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM docker.io/library/python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.1 && groupadd --gid 10001 commander && useradd --uid 10001 --gid 10001 --create-home commander
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY commander/ commander/
COPY --from=frontend /build/frontend/dist frontend/dist
RUN mkdir -p /data/notes && chown -R commander:commander /data /app
USER commander
ENV PATH="/app/.venv/bin:$PATH" WORKSPACE_ROOT=/data/notes
EXPOSE 8000
CMD ["uvicorn", "commander.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
