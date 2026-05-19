# SINPE Bridge API

FastAPI backend para validar pagos SINPE Móvil.

## Quick Start

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Linux/Mac (Bash)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

Copiar `.env.example` a `.env` para configurar:

```bash
cp .env.example .env
```

En development, los valores por defecto funcionan. Para production, actualizar:
- `DATABASE_URL`: PostgreSQL connection string
- `API_KEY`: Debe coincidir con el Worker API_KEY
- `DEBUG`: False
- `LOG_LEVEL`: INFO

## Endpoints

- `POST /api/v1/payments` - Procesar SMS
- `POST /api/v1/uploads/receipts` - Subir imágenes
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /api/v1/docs` - API documentation

## Architecture

- `app/api/` - Endpoints HTTP
- `app/domain/` - Business logic
- `app/infrastructure/` - Database, external services
- `app/core/` - Config, security, middleware
- `app/shared/` - Utilities, constants


