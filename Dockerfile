# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN uv sync --frozen --no-dev --no-install-project --no-cache

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY src/ ./src/
COPY main.py ./
COPY .env.example ./.env.example
COPY README.md ./
COPY pyproject.toml ./
COPY uv.lock ./

RUN groupadd -r appuser && useradd -m -r -g appuser appuser

RUN mkdir -p storage uploads processed temp models logs assets && \
    chown -R appuser:appuser /app /home/appuser

ARG HUGGINGFACE_TOKEN
ARG DOWNLOAD_MODEL=false
RUN if [ "$DOWNLOAD_MODEL" = "true" ] && [ -n "$HUGGINGFACE_TOKEN" ]; then \
        echo "Downloading model during build..." && \
        uv run python main.py download-model --auth-token "$HUGGINGFACE_TOKEN"; \
    else \
        echo "Skipping model download during build"; \
    fi && \
    rm -rf /root/.cache/huggingface

USER appuser

EXPOSE 8000

ENTRYPOINT ["uv", "run", "python", "main.py"]

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
