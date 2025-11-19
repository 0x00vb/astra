# Astra Backend

FastAPI backend with PostgreSQL, SQLAlchemy, and health checks.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Copy and update `.env` file with your database credentials:
   ```bash
   DB_USER=your_postgres_user
   DB_PASSWORD=your_postgres_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=astra
   SECRET_KEY=your_secret_key_here
   ```

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/api/health
   ```

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration with Pydantic
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py    # Health check endpoint
│   ├── core/
│   │   └── __init__.py
│   └── db/
│       ├── models/
│       │   └── __init__.py
│       └── session.py    # Database session and engine
├── requirements.txt
└── run.py
```
