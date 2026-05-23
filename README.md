# SINPE Bridge API

FastAPI backend para validar y conciliar pagos SINPE Móvil con órdenes de POS.

## Stack

- **Framework**: FastAPI + Python 3.12
- **Base de datos**: Supabase (PostgreSQL 15) vía asyncpg + SQLAlchemy async
- **Deploy**: Fly.io (`sinpe-bridge-api.fly.dev`)
- **Proxy**: Cloudflare Worker en `api.tonyml.com`

---

## Arquitectura

```
Android App (SMS listener)
    ↓
api.tonyml.com
    ↓
Cloudflare Worker (proxy-apy-bridgesimpe)
    ↓
https://sinpe-bridge-api.fly.dev
    ↓
Supabase PostgreSQL
```

---

## Desarrollo local

### Requisitos
- Python 3.12+
- PostgreSQL local o conexión a Supabase

### Setup

```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Editar .env con tus valores
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus valores
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Variables de entorno (.env)

```env
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
API_KEY=468bc1becd1b92ff7a6cdeafa31e891d
DEBUG=True
LOG_LEVEL=INFO
```

> En desarrollo sin `DATABASE_URL`, el backend cae a SQLite automáticamente.

---

## Deploy en Fly.io

### Primer deploy (solo una vez)

```powershell
# Instalar flyctl
iwr https://fly.io/install.ps1 -useb | iex

# Login
fly auth login

# Crear el app
fly apps create sinpe-bridge-api

# Configurar secret de base de datos
fly secrets set DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres" -a sinpe-bridge-api

# Deploy
fly deploy
```

### Deploys posteriores

```powershell
fly deploy
```

### Comandos útiles

```powershell
# Ver logs en vivo
fly logs -a sinpe-bridge-api

# Ver secrets configurados
fly secrets list -a sinpe-bridge-api

# SSH a la máquina
fly ssh console -a sinpe-bridge-api

# Ver estado de las máquinas
fly status -a sinpe-bridge-api
```

### Configuración de costos (fly.toml)

El deploy está configurado para costo mínimo (~$0/mes con el crédito gratuito de $5):

```toml
auto_stop_machines = "stop"   # Apaga la VM cuando no hay tráfico
auto_start_machines = true    # La enciende al llegar una request
min_machines_running = 0      # Nunca mantiene VMs activas 24/7
memory = "256mb"              # Mínimo viable para FastAPI
```

---

## Endpoints

### Health

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/` | Info del servicio |
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness check |

### Payments (Mensajes SINPE)

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/payments` | Recibir mensaje SINPE desde Android |
| `GET` | `/api/v1/payments/{message_id}` | Consultar mensaje por UUID |
| `GET` | `/api/v1/payments?id_pos=...` | Listar mensajes de un POS |

### Orders (Órdenes de compra)

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/orders` | Crear orden de compra desde POS |
| `GET` | `/api/v1/orders/{order_number}` | Obtener orden por número |
| `GET` | `/api/v1/orders?id_pos=...` | Listar órdenes de un POS |

### Uploads

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/uploads/receipts` | Subir imagen de comprobante |
| `POST` | `/api/v1/uploads/qr` | Subir imagen de QR |
| `GET` | `/api/v1/uploads/{upload_id}` | Obtener metadata de upload |
| `DELETE` | `/api/v1/uploads/{upload_id}` | Eliminar upload |

### Documentación interactiva

- **Swagger UI**: `https://sinpe-bridge-api.fly.dev/api/v1/docs`
- **OpenAPI JSON**: `https://sinpe-bridge-api.fly.dev/api/v1/openapi.json`

---

## Enums de base de datos

Supabase usa tipos ENUM estrictos. Los valores válidos son:

### payment_method
```
sinpe | card | cash | transfer
```

### order_status
```
pending | matched | confirmed | review | expired | rejected
```

### session_status
```
pending | matched | confirmed | review | unmatched | expired
```

### match_method
```
token | scoring | manual | none
```

---

## Estructura del proyecto

```
sinpe-bridge-api/
├── app/
│   ├── api/
│   │   ├── deps.py              ← Dependencias (DB session)
│   │   └── v1/
│   │       ├── router.py        ← Router principal
│   │       └── endpoints/
│   │           ├── orders.py
│   │           ├── payments.py
│   │           └── uploads.py
│   ├── core/
│   │   ├── config.py            ← Settings (pydantic-settings)
│   │   └── middleware.py        ← TraceMiddleware
│   ├── domain/
│   │   ├── orders/
│   │   │   ├── schemas.py       ← Pydantic models
│   │   │   ├── service.py       ← Lógica de negocio
│   │   │   └── repository.py   ← Acceso a DB
│   │   └── payments/
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── repository.py
│   ├── infrastructure/
│   │   └── db/
│   │       ├── base.py          ← Base declarativa SQLAlchemy
│   │       ├── models.py        ← Modelos ORM
│   │       └── session.py       ← Engine + get_db
│   └── main.py                  ← App FastAPI + middleware + routers
├── Dockerfile
├── fly.toml
└── requirements.txt
```

---

## Base de datos (Supabase)

Las tablas principales son:

- `purchase_orders` — Órdenes del POS
- `sinpe_raw_messages` — Mensajes SINPE recibidos desde Android
- `correlation_sessions` — Sesiones de correlación orden ↔ pago
- `sinpe_image_receipts` — Imágenes de comprobantes con OCR

El schema completo está en los archivos SQL del proyecto.

> **Nota**: El campo `correlation_token` en `purchase_orders` es máximo 8 caracteres.
> Es el token corto que el cajero le dice al cliente para poner en el concepto SINPE.
