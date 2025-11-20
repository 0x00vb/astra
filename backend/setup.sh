#!/bin/bash
# Script de configuración para desarrollo local con uv

set -e

echo "🚀 Configurando entorno de desarrollo local con uv..."

# Verificar si uv está instalado
if ! command -v uv &> /dev/null; then
    echo "❌ uv no está instalado"
    echo "📦 Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv instalado"
    echo "⚠️  Por favor, reinicia tu terminal o ejecuta: source ~/.cargo/env"
    exit 1
fi

echo "✅ uv encontrado"

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual..."
    uv venv
    echo "✅ Entorno virtual creado"
else
    echo "ℹ️  Entorno virtual ya existe"
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source .venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias desde pyproject.toml..."
uv pip install -e .

echo ""
echo "✅ ¡Configuración completada!"
echo ""
echo "Para activar el entorno virtual en el futuro:"
echo "  source .venv/bin/activate"
echo ""
echo "Para ejecutar el servidor:"
echo "  python run.py"
echo ""

