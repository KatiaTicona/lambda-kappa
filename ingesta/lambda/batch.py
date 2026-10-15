import argparse, time

import psycopg2
from psycopg2 import errors

def ciclo(conn):
    """Recalcula la vista batch completa y retira de la vista speed lo ya cubierto."""
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT batch_seq FROM lambda_meta WHERE id = 1 FOR UPDATE")
            prev = cur.fetchone()[0]
            cur.execute("SELECT coalesce(max(seq), 0) FROM lambda_raw")
            w = cur.fetchone()[0]
            if w == prev:
                return 0

            # 1) recomputo completo desde el master dataset
            cur.execute("DELETE FROM lambda_batch_view")
            cur.execute("""
                INSERT INTO lambda_batch_view
                SELECT date_trunc('minute', ts), event_type, count(*), sum(amount)
                FROM lambda_raw WHERE seq <= %s GROUP BY 1, 2
            """, (w,))

            # 2) restar de la vista speed solo los eventos recien cubiertos
            cur.execute("""
                WITH d AS (
                  SELECT date_trunc('minute', ts) AS m, event_type AS t,
                         count(*) AS n, sum(amount) AS s
                  FROM lambda_raw WHERE seq > %s AND seq <= %s GROUP BY 1, 2
                )
                UPDATE lambda_speed_view v
                SET n = v.n - d.n, total = v.total - d.s
                FROM d WHERE v.minute = d.m AND v.event_type = d.t
            """, (prev, w))
            cur.execute("DELETE FROM lambda_speed_view WHERE n <= 0")

            cur.execute("UPDATE lambda_meta SET batch_seq = %s WHERE id = 1", (w,))
            return w - prev

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=15.0, help="segundos entre ciclos batch")
    a = p.parse_args()

    conn = psycopg2.connect(host="localhost", port=5432, dbname="bi", user="bi", password="bi")
    print(f"Batch layer activa (cada {a.interval}s). Ctrl+C para detener.")
    try:
        while True:
            t0 = time.time()
            for intento in range(3):
                try:
                    nuevos = ciclo(conn)
                    break
                except errors.DeadlockDetected:
                    conn.rollback()
                    nuevos = -1
            dur = time.time() - t0
            if nuevos:
                print(f"ciclo batch: {nuevos} eventos nuevos cubiertos en {dur:.2f}s")
            time.sleep(max(0, a.interval - dur))
    except KeyboardInterrupt:
        print("Detenido.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()