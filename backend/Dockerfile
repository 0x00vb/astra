## Imagen backend Astra (FastAPI)
FROM python:3.11-slim

# Evitar problemas de buffering y archivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para compilar algunos paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Crear usuario no-root para seguridad (antes de copiar código)
RUN useradd -m -u 1000 appuser

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Instalar dependencias de Python usando uv
# Primero instalar PyTorch (requiere index URL especial)
RUN uv pip install --system --no-cache torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Instalar el resto de dependencias desde pyproject.toml
RUN uv pip install --system --no-cache .

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Healthcheck sencillo contra el endpoint de salud
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Comando por defecto (puede ser sobrescrito en docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

#

