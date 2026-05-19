from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="SINPE Bridge API",
    description="Valida pagos SINPE Móvil y los concilia con órdenes del POS.",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok"}
