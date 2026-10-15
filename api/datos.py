import os
import threading
from contextlib import contextmanager

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

DSN = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname="bi", user="bi", password="bi",
)
MAXCONN = 30
_pool = ThreadedConnectionPool(2, MAXCONN, **DSN)
_sem = threading.BoundedSemaphore(MAXCONN)

# lista blanca: evita inyeccion SQL en el nombre de la tabla
TABLAS = {"lambda": "lambda_serving", "kappa": "kappa_view"}


@contextmanager
def _cursor():
    with _sem:
        conn = _pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
        finally:
            _pool.putconn(conn)   # hace rollback si quedo una transaccion abierta


def _tabla(fuente: str) -> str:
    if fuente not in TABLAS:
        raise ValueError(f"fuente invalida: {fuente!r} (use 'lambda' o 'kappa')")
    return TABLAS[fuente]


def salud():
    with _cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def resumen(fuente: str):
    t = _tabla(fuente)
    sql = f"""
        SELECT event_type,
               sum(n)::bigint AS eventos,
               round(sum(total), 2) AS monto,
               round(sum(total) / nullif(sum(n), 0), 2) AS promedio,
               max(last_event_ts) AS ultimo_evento
        FROM {t}
        GROUP BY event_type
        ORDER BY event_type
    """
    with _cursor() as cur:
        cur.execute(sql)
        filas = cur.fetchall()
    return [
        {
            "event_type": r["event_type"],
            "eventos": int(r["eventos"]),
            "monto": float(r["monto"]),
            "promedio": float(r["promedio"]) if r["promedio"] is not None else None,
            "ultimo_evento": r["ultimo_evento"].isoformat() if r["ultimo_evento"] else None,
        }
        for r in filas
    ]


def serie(fuente: str, tipo, minutos: int):
    t = _tabla(fuente)
    sql = f"""
        SELECT minute, sum(n)::bigint AS eventos, round(sum(total), 2) AS monto
        FROM {t}
        WHERE minute >= (SELECT max(minute) FROM {t}) - make_interval(mins => %s)
          AND (%s::text IS NULL OR event_type = %s)
        GROUP BY minute
        ORDER BY minute
    """
    with _cursor() as cur:
        cur.execute(sql, (minutos, tipo, tipo))
        filas = cur.fetchall()
    return [
        {"minute": r["minute"].isoformat(), "eventos": int(r["eventos"]), "monto": float(r["monto"])}
        for r in filas
    ]