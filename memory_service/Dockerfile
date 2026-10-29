FROM docker.io/library/python:3.13-slim-bookworm@sha256:4cea12ab7d78a3312c85f8cab19b6971d4fe9704da25443986c0bc20a6678850
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy \
    MEM0_TELEMETRY=false ANONYMIZED_TELEMETRY=false HF_HOME=/opt/models \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.1 && groupadd --gid 10002 memory && useradd --uid 10002 --gid 10002 --create-home memory
COPY memory_service/pyproject.toml memory_service/uv.lock ./
RUN uv sync --frozen --no-dev
COPY memory_service/ /app/memory_service/
RUN .venv/bin/python -c 'from sentence_transformers import SentenceTransformer; from memory_service.backend import MODEL,REVISION; SentenceTransformer(MODEL, revision=REVISION, device="cpu", trust_remote_code=False)'
ENV PATH="/app/.venv/bin:$PATH" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER memory
EXPOSE 8090
CMD ["uvicorn", "memory_service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8090", "--no-access-log", "--workers", "1", "--limit-concurrency", "8", "--timeout-keep-alive", "5"]
