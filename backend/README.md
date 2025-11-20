# Backend Astra

Backend FastAPI para el proyecto Astra.

## 📋 Requisitos Previos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Gestor de paquetes rápido para Python

## 🚀 Instalación Local

### 1. Instalar uv

Si aún no tienes `uv` instalado:

```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# O con pip (temporalmente)
pip install uv
```

### 2. Crear entorno virtual

```bash
cd backend
uv venv
```

Esto creará un entorno virtual en `.venv/` (o puedes especificar otro nombre con `uv venv nombre_env`).

### 3. Activar el entorno virtual

```bash
# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. Instalar dependencias

```bash
# Instalar todas las dependencias desde pyproject.toml
uv pip install -e .

# O si prefieres instalar PyTorch primero (CPU)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
uv pip install -e .
```

### 5. Verificar instalación

```bash
python -c "import fastapi; print('FastAPI instalado correctamente')"
```

## 🔧 Desarrollo

### Ejecutar el servidor

```bash
python run.py
```

O directamente con uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Ejecutar tests

```bash
pytest
```

### Ejecutar scripts

```bash
# Indexar embeddings para documentos
python scripts/ingest_and_index.py --all
```

## 📦 Gestión de Dependencias

### Agregar una nueva dependencia

```bash
# Agregar al pyproject.toml y luego instalar
uv pip install nombre-paquete
uv pip freeze > temp_requirements.txt  # Para ver la versión exacta
# Luego agregar manualmente al pyproject.toml
```

O editar directamente `pyproject.toml` y luego:

```bash
uv pip install -e .
```

### Actualizar dependencias

```bash
uv pip install -e . --upgrade
```

### Ver dependencias instaladas

```bash
uv pip list
```

## 🐳 Docker

Ver la documentación principal en `/docs/DOCKER.md` para usar Docker.

## 📝 Notas

- El proyecto usa `uv` como gestor de paquetes en lugar de `pip`
- Las dependencias están definidas en `pyproject.toml`
- El entorno virtual antiguo `venv/` puede ser eliminado si ya no lo necesitas

