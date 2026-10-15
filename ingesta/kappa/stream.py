import argparse, json, time
from collections import defaultdict
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from confluent_kafka import Consumer

UPSERT = """
INSERT INTO kappa_view (minute, event_type, n, total, last_event_ts, last_processed_at)
VALUES %s
ON CONFLICT (minute, event_type) DO UPDATE SET
  n = kappa_view.n + EXCLUDED.n,
  total = kappa_view.total + EXCLUDED.total,
  last_event_ts = GREATEST(kappa_view.last_event_ts, EXCLUDED.last_event_ts),
  last_processed_at = now()
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="eventos")
    p.add_argument("--group", default="kappa", help="cambiar para reprocesar desde el inicio")
    p.add_argument("--flush", type=float, default=1.0, help="segundos entre escrituras")
    p.add_argument("--max-batch", type=int, default=2000)
    p.add_argument("--truncate", action="store_true", help="vaciar kappa_view antes de empezar")
    a = p.parse_args()

    conn = psycopg2.connect(host="localhost", port=5432, dbname="bi", user="bi", password="bi")
    if a.truncate:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE kappa_view")
        conn.commit()

    c = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": a.group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    c.subscribe([a.topic])

    agg = {}          # (minuto, tipo) -> [n, total, ultimo_ts]
    pendientes = 0
    t_flush = time.time()
    procesados = 0

    def flush():
        nonlocal agg, pendientes, t_flush
        if agg:
            filas = [(m, t, v[0], v[1], v[2]) for (m, t), v in agg.items()]
            with conn.cursor() as cur:
                execute_values(cur, UPSERT, filas, template="(%s,%s,%s,%s,%s,now())")
            conn.commit()
            c.commit(asynchronous=False)   # offset solo despues de escribir en la BD
        agg, pendientes, t_flush = {}, 0, time.time()

    print(f"Kappa activo (grupo={a.group}). Ctrl+C para detener.")
    try:
        while True:
            msg = c.poll(0.2)
            if msg is not None and not msg.error():
                ev = json.loads(msg.value())
                ts = datetime.fromisoformat(ev["ts"])
                clave = (ts.replace(second=0, microsecond=0), ev["event_type"])
                v = agg.setdefault(clave, [0, 0.0, ts])
                v[0] += 1
                v[1] += ev["amount"]
                v[2] = max(v[2], ts)
                pendientes += 1
                procesados += 1
            if pendientes >= a.max_batch or (pendientes and time.time() - t_flush >= a.flush):
                flush()
    except KeyboardInterrupt:
        flush()
        print(f"Detenido. Eventos procesados: {procesados}")
    finally:
        c.close()
        conn.close()

if __name__ == "__main__":
    main()
    