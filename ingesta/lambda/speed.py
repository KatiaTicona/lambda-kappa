import argparse, json, time
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from confluent_kafka import Consumer

INSERT_RAW = """
INSERT INTO lambda_raw (event_id, user_id, event_type, amount, ts)
VALUES %s
ON CONFLICT (event_id) DO NOTHING
RETURNING ts, event_type, amount
"""

UPSERT_SPEED = """
INSERT INTO lambda_speed_view (minute, event_type, n, total, last_event_ts, last_processed_at)
VALUES %s
ON CONFLICT (minute, event_type) DO UPDATE SET
  n = lambda_speed_view.n + EXCLUDED.n,
  total = lambda_speed_view.total + EXCLUDED.total,
  last_event_ts = GREATEST(lambda_speed_view.last_event_ts, EXCLUDED.last_event_ts),
  last_processed_at = now()
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="eventos")
    p.add_argument("--group", default="lambda-speed")
    p.add_argument("--flush", type=float, default=1.0)
    p.add_argument("--max-batch", type=int, default=2000)
    a = p.parse_args()

    conn = psycopg2.connect(host="localhost", port=5432, dbname="bi", user="bi", password="bi")
    c = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": a.group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    c.subscribe([a.topic])

    buf = []
    t_flush = time.time()
    procesados = 0

    def flush():
        nonlocal buf, t_flush
        if buf:
            with conn.cursor() as cur:
                # 1) master dataset: guarda crudo; devuelve solo los eventos nuevos (deduplica)
                nuevos = execute_values(cur, INSERT_RAW, buf, fetch=True)
                # 2) vista incremental solo con los eventos nuevos
                agg = {}
                for ts, tipo, monto in nuevos:
                    clave = (ts.replace(second=0, microsecond=0), tipo)
                    v = agg.setdefault(clave, [0, 0.0, ts])
                    v[0] += 1
                    v[1] += float(monto)
                    v[2] = max(v[2], ts)
                filas = sorted((m, t, v[0], v[1], v[2]) for (m, t), v in agg.items())
                if filas:
                    execute_values(cur, UPSERT_SPEED, filas, template="(%s,%s,%s,%s,%s,now())")
            conn.commit()                     # raw + vista speed en una sola transaccion
            c.commit(asynchronous=False)      # offset solo despues de escribir en la BD
        buf, t_flush = [], time.time()

    print(f"Speed layer activa (grupo={a.group}). Ctrl+C para detener.")
    try:
        while True:
            msg = c.poll(0.2)
            if msg is not None and not msg.error():
                ev = json.loads(msg.value())
                buf.append((ev["event_id"], ev["user_id"], ev["event_type"],
                            ev["amount"], datetime.fromisoformat(ev["ts"])))
                procesados += 1
            if len(buf) >= a.max_batch or (buf and time.time() - t_flush >= a.flush):
                flush()
    except KeyboardInterrupt:
        flush()
        print(f"Detenido. Eventos leidos: {procesados}")
    finally:
        c.close()
        conn.close()

if __name__ == "__main__":
    main()