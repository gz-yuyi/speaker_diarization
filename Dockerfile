# Use Python 3.12 slim image as base
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml uv.lock ./

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies using uv sync with lock file (no local package)
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# Copy application code after dependencies are installed
COPY src/ ./src/
COPY main.py ./
COPY .env.example ./.env.example
COPY README.md ./

# Create necessary directories and set permissions
RUN mkdir -p storage uploads processed temp models logs assets && \
    chown -R appuser:appuser /app

# Download model during build (requires build-arg)
ARG HUGGINGFACE_TOKEN
RUN if [ -n "$HUGGINGFACE_TOKEN" ]; then \
        echo "Downloading model during build..." && \
        cd /app && \
        uv run python main.py download-model --auth-token $HUGGINGFACE_TOKEN || echo "Model download failed, will download at runtime"; \
    else \
        echo "No HUGGINGFACE_TOKEN provided, model will be downloaded at runtime"; \
    fi

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default entrypoint
ENTRYPOINT ["uv", "run", "python", "main.py"]

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
