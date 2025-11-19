#!/bin/bash

# Script de inicio rápido para el proyecto Astra
# Uso: ./docker-start.sh [dev|prod]

set -e

ENV=${1:-dev}

echo "🚀 Iniciando proyecto Astra en modo: $ENV"

if [ "$ENV" = "prod" ]; then
    if [ ! -f ".env.prod" ]; then
        echo "❌ Error: Archivo .env.prod no encontrado"
        echo "📝 Crea el archivo .env.prod basándote en .env.example"
        exit 1
    fi
    echo "📦 Construyendo y levantando servicios de producción..."
    docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
    echo "✅ Servicios de producción iniciados"
    echo "📊 Ver logs: docker-compose -f docker-compose.prod.yml logs -f"
else
    if [ ! -f ".env" ]; then
        echo "📝 Creando archivo .env desde .env.example..."
        cp .env.example .env
        echo "✅ Archivo .env creado. Puedes editarlo si es necesario."
    fi
    echo "🔧 Construyendo y levantando servicios de desarrollo..."
    docker compose up -d --build
    echo "✅ Servicios de desarrollo iniciados"
    echo ""
    echo "🌐 Accede a:"
    echo "   - Frontend: http://localhost:3000"
    echo "   - Backend API: http://localhost:8000"
    echo "   - API Docs: http://localhost:8000/docs"
    echo ""
    echo "📊 Ver logs: docker-compose logs -f"
fi

echo ""
echo "📋 Estado de los servicios:"
if [ "$ENV" = "prod" ]; then
    docker compose -f docker-compose.prod.yml ps
else
    docker compose ps
fi

