# lambda-kappa: comparación de arquitecturas de ingesta y de API

Actividad N°1 – Business Intelligence (Maestría en Informática, UNA Puno).
Plataforma de ingesta de eventos con dos arquitecturas de procesamiento
(**Lambda** y **Kappa**) y dos estilos de API (**REST** y **GraphQL**),
con benchmark de rendimiento reproducible.

## Arquitectura

```
generador ──► Redpanda (Kafka) ──┬─► Kappa:  stream.py ───────────────► kappa_view ──┐
                                 └─► Lambda: speed.py ─► lambda_raw                  │
                                             speed.py ─► lambda_speed_view ─┐        ├─► PostgreSQL ─► API REST (FastAPI)
                                             batch.py ─► lambda_batch_view ─┴► lambda_serving ──┘                └► API GraphQL (Strawberry)
```

- **Kappa**: un solo pipeline de streaming; el reprocesamiento se hace repitiendo el log.
- **Lambda**: capa speed (incremental) + capa batch (recálculo completo periódico) + vista de servicio.
- Ambas APIs exponen las mismas consultas (`resumen`, `serie`) sobre la misma base de datos.

## Requisitos

Docker Desktop, Python 3.10+.

## Cómo reproducir

```powershell
git clone https://github.com/KatiaTicona/lambda-kappa.git
cd lambda-kappa
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d
```

Probar a mano (4 terminales): `ingesta/kappa/stream.py`, `ingesta/lambda/speed.py`,
`ingesta/lambda/batch.py --interval 15` y `generador/generador.py --rate 500 --total 20000`.

APIs: `python -m uvicorn api.rest.main:app --port 8000` y
`python -m uvicorn api.graphql.main:app --port 8001`.

## Benchmark

```powershell
python -m benchmark.bench_ingesta --rates 500,2000,5000 --duracion 30 --reps 3
python -m benchmark.bench_ingesta --rates 5000 --duracion 30 --reps 3 --reproceso --out benchmark\resultados\reproceso.csv
python -m benchmark.poblar
python -m benchmark.bench_api --usuarios 10,50,200 --duracion 40 --reps 3
python -m benchmark.resumen
```

Los datos crudos están en `benchmark/resultados/*.csv`; las tablas en `resumen.md`
y la figura en `figura_resumen.png`.

## Resultados

(Pegar aquí las tablas principales de `benchmark/resultados/resumen.md`
y la imagen `figura_resumen.png`.)

## Limitaciones

- Todo corre en una sola laptop, por lo que los valores sirven para comparar entre
  arquitecturas bajo las mismas condiciones, no como valores absolutos.
- Una partición de Redpanda y un worker por capa; Lambda asume un solo worker de speed.
- Ambas arquitecturas escriben cada 1 s, un piso de latencia común.
- 3 repeticiones por configuración: diferencias menores a una desviación estándar no son concluyentes.

## Estructura

`generador/` · `ingesta/kappa/` · `ingesta/lambda/` · `api/` · `benchmark/` · `db/init.sql` · `docker-compose.yml`

## Autoría

Katia Ticona Casa – Maestría en Informática (Gerencia de TIC), UNA Puno.