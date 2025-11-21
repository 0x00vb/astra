FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# --- CACHE LAYER START ---
# 1. Copy ONLY dependency files first
COPY pyproject.toml uv.lock* ./

# 2. Install dependencies (This layer is now CACHED unless you change pyproject.toml)
# We use --system so we don't need to manage venv activation inside Docker
RUN uv pip install --system --no-cache torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN uv pip install --system --no-cache -r pyproject.toml
# --- CACHE LAYER END ---

# Create user
RUN useradd -m -u 1000 appuser

# 3. Copy the rest of the code (This changes frequently, but won't trigger re-install)
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]