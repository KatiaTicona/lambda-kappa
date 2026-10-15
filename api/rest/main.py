from typing import Literal, Optional

from fastapi import FastAPI, Query
from starlette.concurrency import run_in_threadpool

from api import datos

app = FastAPI(title="API REST - lambda-kappa")
Fuente = Literal["lambda", "kappa"]


@app.get("/health")
async def health():
    await run_in_threadpool(datos.salud)
    return {"ok": True}


@app.get("/resumen")
async def resumen(fuente: Fuente = "kappa"):
    return await run_in_threadpool(datos.resumen, fuente)


@app.get("/serie")
async def serie(
    fuente: Fuente = "kappa",
    tipo: Optional[str] = None,
    minutos: int = Query(60, ge=1, le=1440),
):
    return await run_in_threadpool(datos.serie, fuente, tipo, minutos)