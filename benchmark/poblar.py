import argparse, time

from benchmark.bench_ingesta import conectar, crear_topic, detener, lanzar, producir, reset_db


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--total", type=int, default=200000)
    p.add_argument("--rate", type=int, default=5000)
    p.add_argument("--batch-interval", type=float, default=5.0)
    a = p.parse_args()

    reset_db()
    topic = f"poblar-{int(time.time())}"
    crear_topic(topic)
    k, _ = lanzar(["ingesta/kappa/stream.py", "--topic", topic, "--group", f"k-{topic}"])
    s, _ = lanzar(["ingesta/lambda/speed.py", "--topic", topic, "--group", f"s-{topic}"])
    b, _ = lanzar(["ingesta/lambda/batch.py", "--interval", str(a.batch_interval)])
    time.sleep(6)
    producir(topic, a.rate, a.total, seed=1)

    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    def n(tabla):
        cur.execute(f"SELECT coalesce(sum(n), 0) FROM {tabla}")
        return int(cur.fetchone()[0])

    limite = time.time() + 900
    while time.time() < limite and (n("kappa_view") < a.total or n("lambda_serving") < a.total):
        time.sleep(1)
    time.sleep(a.batch_interval + 3)
    print(f"kappa_view = {n('kappa_view')} | lambda_serving = {n('lambda_serving')} | esperado = {a.total}")
    detener([k, s, b])


if __name__ == "__main__":
    main()