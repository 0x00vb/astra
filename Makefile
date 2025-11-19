.PHONY: help dev prod up down build logs clean restart shell-backend shell-frontend shell-db db-backup db-restore migrate

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Iniciar en modo desarrollo
	@if [ ! -f .env ]; then cp .env.example .env; fi
	docker-compose up -d --build
	@echo "✅ Servicios iniciados en modo desarrollo"
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🌐 Backend: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/docs"

prod: ## Iniciar en modo producción
	@if [ ! -f .env.prod ]; then echo "❌ Error: .env.prod no existe"; exit 1; fi
	docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
	@echo "✅ Servicios iniciados en modo producción"

up: ## Levantar servicios (desarrollo)
	docker-compose up -d

down: ## Detener servicios
	docker-compose down

down-prod: ## Detener servicios de producción
	docker-compose -f docker-compose.prod.yml down

build: ## Construir imágenes
	docker-compose build --no-cache

logs: ## Ver logs de todos los servicios
	docker-compose logs -f

logs-backend: ## Ver logs del backend
	docker-compose logs -f backend

logs-frontend: ## Ver logs del frontend
	docker-compose logs -f frontend

logs-db: ## Ver logs de la base de datos
	docker-compose logs -f postgres

clean: ## Limpiar contenedores, imágenes y volúmenes
	docker-compose down -v --rmi all
	@echo "⚠️  Todos los datos han sido eliminados"

restart: ## Reiniciar servicios
	docker-compose restart

shell-backend: ## Abrir shell en el contenedor del backend
	docker-compose exec backend bash

shell-frontend: ## Abrir shell en el contenedor del frontend
	docker-compose exec frontend sh

shell-db: ## Abrir psql en la base de datos
	docker-compose exec postgres psql -U postgres -d astra_db

db-backup: ## Crear backup de la base de datos
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres astra_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup creado en backups/"

db-restore: ## Restaurar backup de la base de datos (uso: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then echo "❌ Error: Especifica el archivo con FILE=backup.sql"; exit 1; fi
	docker-compose exec -T postgres psql -U postgres astra_db < $(FILE)
	@echo "✅ Backup restaurado"

migrate: ## Ejecutar migraciones de Alembic
	docker-compose exec backend alembic upgrade head

migrate-create: ## Crear nueva migración (uso: make migrate-create MSG="descripción")
	@if [ -z "$(MSG)" ]; then echo "❌ Error: Especifica mensaje con MSG=\"descripción\""; exit 1; fi
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

ps: ## Ver estado de los servicios
	docker-compose ps

stats: ## Ver estadísticas de uso de recursos
	docker stats

