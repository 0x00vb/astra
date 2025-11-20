# Guía de Dockerización - Proyecto Astra

Esta guía te ayudará a ejecutar y deployar todo el stack de Astra usando Docker y Docker Compose.

## 📋 Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git

## 🚀 Inicio Rápido

### Opción 1: Script Automático (Recomendado)

```bash
# Desarrollo
./docker-start.sh dev

# Producción
./docker-start.sh prod
```

### Opción 2: Makefile

```bash
# Ver todos los comandos disponibles
make help

# Desarrollo
make dev

# Producción
make prod
```

### Opción 3: Docker Compose Manual

#### Desarrollo

1. **Clonar el repositorio** (si aún no lo has hecho):
   ```bash
   git clone <tu-repositorio>
   cd astra
   ```

2. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con tus valores si es necesario
   ```

3. **Levantar todo el stack con un solo comando**:
   ```bash
   docker-compose up -d
   ```

4. **Ver los logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Acceder a las aplicaciones**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs (Swagger): http://localhost:8000/docs

### Producción

1. **Configurar variables de entorno de producción**:
   ```bash
   cp .env.example .env.prod
   # Editar .env.prod con valores seguros de producción
   # IMPORTANTE: Cambiar SECRET_KEY por una clave segura
   ```

2. **Levantar el stack de producción**:
   ```bash
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

3. **Verificar que todo esté funcionando**:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker-compose -f docker-compose.prod.yml logs -f
   ```

## 📁 Estructura de Archivos Docker

```
astra/
├── backend/
│   ├── Dockerfile              # Producción optimizado
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile              # Producción optimizado
│   ├── Dockerfile.dev          # Desarrollo con hot reload
│   └── .dockerignore
├── docker-compose.yml          # Configuración desarrollo
├── docker-compose.prod.yml     # Configuración producción
├── .env.example                # Plantilla de variables de entorno
└── DOCKER.md                   # Esta guía
```

## 🔧 Comandos Útiles

### Usando Makefile (Recomendado)

```bash
make help              # Ver todos los comandos disponibles
make dev               # Iniciar desarrollo
make prod              # Iniciar producción
make logs              # Ver logs de todos los servicios
make logs-backend      # Ver logs del backend
make logs-frontend     # Ver logs del frontend
make shell-backend     # Abrir shell en backend
make shell-frontend    # Abrir shell en frontend
make shell-db          # Abrir psql
make db-backup         # Crear backup de BD
make migrate           # Ejecutar migraciones
make clean             # Limpiar todo (⚠️ elimina datos)
```

### Docker Compose Manual

#### Desarrollo

```bash
# Levantar servicios
docker-compose up -d

# Levantar y reconstruir imágenes
docker-compose up -d --build

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ elimina datos de BD)
docker-compose down -v

# Ejecutar comandos en un contenedor
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec postgres psql -U postgres -d astra_db

# Reconstruir un servicio específico
docker-compose build backend
docker-compose up -d --no-deps backend
```

### Producción

```bash
# Levantar servicios de producción
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Reconstruir y levantar
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Detener servicios
docker-compose -f docker-compose.prod.yml down

# Actualizar servicios (pull + rebuild + restart)
docker-compose -f docker-compose.prod.yml --env-file .env.prod pull
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 🗄️ Base de Datos

### Acceder a PostgreSQL

```bash
# Desde el host
docker-compose exec postgres psql -U postgres -d astra_db

# O usando variables de entorno
docker-compose exec postgres psql -U $DB_USER -d $DB_NAME
```

### Backup de Base de Datos

```bash
# Crear backup
docker-compose exec postgres pg_dump -U postgres astra_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker-compose exec -T postgres psql -U postgres astra_db < backup.sql
```

### Migraciones de Base de Datos

```bash
# Ejecutar migraciones Alembic
docker-compose exec backend alembic upgrade head

# Crear nueva migración
docker-compose exec backend alembic revision --autogenerate -m "descripción"
```

## 🔍 Troubleshooting

### Los servicios no inician

1. **Verificar que los puertos no estén en uso**:
   ```bash
   # Linux/Mac
   lsof -i :3000
   lsof -i :8000
   lsof -i :5432
   
   # Windows
   netstat -ano | findstr :3000
   ```

2. **Ver logs de errores**:
   ```bash
   docker-compose logs
   ```

3. **Verificar variables de entorno**:
   ```bash
   docker-compose config
   ```

### El frontend no se conecta al backend

1. **Verificar que NEXT_PUBLIC_API_URL esté configurado correctamente**:
   - En desarrollo: `http://localhost:8000`
   - En producción: usar la URL real del backend

2. **Verificar que el backend esté corriendo**:
   ```bash
   docker-compose ps
   curl http://localhost:8000/api/health
   ```

### Problemas con volúmenes de datos

```bash
# Ver volúmenes
docker volume ls

# Inspeccionar un volumen
docker volume inspect astra_postgres_data

# Eliminar un volumen (⚠️ elimina datos)
docker volume rm astra_postgres_data
```

### Reconstruir desde cero

```bash
# Detener y eliminar todo
docker-compose down -v

# Eliminar imágenes
docker-compose down --rmi all

# Reconstruir todo
docker-compose build --no-cache
docker-compose up -d
```

## 🚢 Deploy en Producción

### Opción 1: Servidor con Docker

1. **Clonar el repositorio en el servidor**:
   ```bash
   git clone <tu-repositorio>
   cd astra
   ```

2. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env.prod
   nano .env.prod  # Editar con valores de producción
   ```

3. **Levantar servicios**:
   ```bash
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

4. **Configurar reverse proxy (Nginx)** - Ejemplo:
   ```nginx
   server {
       listen 80;
       server_name tu-dominio.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Opción 2: Docker Swarm (para alta disponibilidad)

```bash
# Inicializar swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml astra

# Ver servicios
docker service ls
```

### Opción 3: Kubernetes

Los archivos docker-compose pueden convertirse a Kubernetes usando herramientas como `kompose`:

```bash
kompose convert -f docker-compose.prod.yml
```

## 🔒 Seguridad en Producción

1. **Cambiar todas las contraseñas por defecto** en `.env.prod`
2. **Usar SECRET_KEY fuerte** (generar con `openssl rand -hex 32`)
3. **No exponer puerto de PostgreSQL** públicamente
4. **Usar HTTPS** con certificados SSL (Let's Encrypt)
5. **Configurar firewall** para limitar acceso
6. **Hacer backups regulares** de la base de datos
7. **Monitorear logs** para detectar problemas

## 📊 Monitoreo y Health Checks

Todos los servicios incluyen health checks:

```bash
# Ver estado de health checks
docker-compose ps

# Verificar health check manualmente
docker inspect --format='{{.State.Health.Status}}' astra_backend_dev
```

## 🧹 Limpieza

```bash
# Eliminar contenedores detenidos
docker-compose down

# Eliminar imágenes no utilizadas
docker image prune

# Limpieza completa (⚠️ elimina todo lo no utilizado)
docker system prune -a --volumes
```

## 📝 Notas Adicionales

- **Hot Reload**: En desarrollo, los cambios en el código se reflejan automáticamente gracias a los volúmenes montados
- **Persistencia**: Los datos de PostgreSQL se guardan en volúmenes Docker
- **Red**: Todos los servicios están en la misma red Docker y pueden comunicarse por nombre de servicio
- **Variables de entorno**: Se pueden sobrescribir desde el archivo `.env` o directamente en docker-compose

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs: `docker-compose logs`
2. Verifica la configuración: `docker-compose config`
3. Consulta la documentación de Docker: https://docs.docker.com/

