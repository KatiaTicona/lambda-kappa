from typing import List, Optional

import strawberry
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from strawberry.fastapi import GraphQLRouter

from api import datos


@strawberry.type
class ResumenTipo:
    event_type: str
    eventos: int
    monto: float
    promedio: Optional[float]
    ultimo_evento: Optional[str]


@strawberry.type
class PuntoSerie:
    minute: str
    eventos: int
    monto: float


@strawberry.type
class Query:
    @strawberry.field
    async def resumen(self, fuente: str = "kappa") -> List[ResumenTipo]:
        filas = await run_in_threadpool(datos.resumen, fuente)
        return [ResumenTipo(**f) for f in filas]

    @strawberry.field
    async def serie(
        self, fuente: str = "kappa", tipo: Optional[str] = None, minutos: int = 60
    ) -> List[PuntoSerie]:
        filas = await run_in_threadpool(datos.serie, fuente, tipo, minutos)
        return [PuntoSerie(**f) for f in filas]


schema = strawberry.Schema(Query)
app = FastAPI(title="API GraphQL - lambda-kappa")
app.include_router(GraphQLRouter(schema), prefix="/graphql")