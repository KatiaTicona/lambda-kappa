"""Benchmark de ingesta: Kappa vs Lambda."""
import argparse, csv, json, os, random, re, subprocess, sys, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import psycopg2
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable
TIPOS = ["consulta", "tramite", "pago", "reclamo"]
RE_CICLO = re.compile(r"ciclo batch: (\d+) eventos nuevos cubiertos en ([\d.]+)s")
CAMPOS = ["arch", "rate_objetivo", "rep", "total", "rate_producido", "completado",
          "t_total_s", "throughput_eps", "lat_p50_s", "lat_p95_s", "lat_p99_s", "lat_max_s",
          "cpu_prom_pct", "rss_max_mb", "batch_ciclos", "batch_dur_prom_s", "batch_dur_max_s",
          "reproceso_s", "flush_s"]


def conectar():
    return psycopg2.connect(host="localhost", port=5432, dbname="bi", user="bi", password="bi")


def reset_db():
    conn = conectar()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE kappa_view, lambda_batch_view, lambda_speed_view")
        cur.execute("TRUNCATE lambda_raw RESTART IDENTITY")
        cur.execute("UPDATE lambda_meta SET batch_seq = 0")
    conn.close()


def crear_topic(nombre):
    admin = AdminClient({"bootstrap.servers": "localhost:9092"})
    for f in admin.create_topics([NewTopic(nombre, num_partitions=1, replication_factor=1)]).values():
        f.result()


def lanzar(args):
    """Lanza un script Python en segundo plano. Devuelve (proceso, lineas_de_salida)."""
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    p = subprocess.Popen([PY, "-u", *args], cwd=RAIZ, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    lineas = []

    def leer():
        for linea in p.stdout:
            lineas.append(linea.strip())

    threading.Thread(target=leer, daemon=True).start()
    return p, lineas


def detener(procesos):
    for p in procesos:
        p.terminate()
    for p in procesos:
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()


class Muestreador(threading.Thread):
    """Mide CPU (% de un nucleo) y memoria (RSS) de unos procesos cada 0.5 s."""
    def __init__(self, pids):
        super().__init__(daemon=True)
        self.procs = [psutil.Process(x) for x in pids]
        self.fin = threading.Event()
        self.cpu, self.rss = [], []

    def run(self):
        for p in self.procs:
            p.cpu_percent(None)
        while not self.fin.wait(0.5):
            try:
                self.cpu.append(sum(p.cpu_percent(None) for p in self.procs))
                self.rss.append(sum(p.memory_info().rss for p in self.procs))
            except psutil.Error:
                break

    def parar(self):
        self.fin.set()
        self.join()


class Sondeo(threading.Thread):
    """Consulta cada 0.1 s cuantos eventos son visibles en la vista de servicio."""
    def __init__(self, tabla):
        super().__init__(daemon=True)
        self.tabla = tabla
        self.fin = threading.Event()
        self.t, self.c = [], []

    def run(self):
        conn = conectar()
        conn.autocommit = True
        with conn.cursor() as cur:
            while not self.fin.is_set():
                cur.execute(f"SELECT coalesce(sum(n), 0) FROM {self.tabla}")
                self.c.append(int(cur.fetchone()[0]))
                self.t.append(time.time())
                time.sleep(0.1)
        conn.close()

    def parar(self):
        self.fin.set()
        self.join()


def producir(topic, rate, total, seed):
    rnd = random.Random(seed)
    prod = Producer({"bootstrap.servers": "localhost:9092", "linger.ms": 5})
    t_sent = np.empty(total)
    inicio = time.perf_counter()
    for i in range(total):
        objetivo = inicio + i / rate
        while True:
            d = objetivo - time.perf_counter()
            if d <= 0:
                break
            if d > 0.002:
                time.sleep(d - 0.001)
        ahora = time.time()
        ev = {
            "event_id": str(uuid.UUID(int=rnd.getrandbits(128))),
            "user_id": rnd.randint(1, 5000),
            "event_type": rnd.choice(TIPOS),
            "amount": round(rnd.uniform(1, 500), 2),
            "ts": datetime.fromtimestamp(ahora, timezone.utc).isoformat(),
        }
        prod.produce(topic, json.dumps(ev).encode())
        t_sent[i] = ahora
        if i % 200 == 0:
            prod.poll(0)
    prod.flush()
    return t_sent


def reproceso(arch, topic, total, flush):
    """Tiempo (con arranque incluido) de reconstruir las vistas desde cero."""
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()
    if arch == "kappa":
        cur.execute("TRUNCATE kappa_view")
        t0 = time.time()
        p, _ = lanzar(["ingesta/kappa/stream.py", "--topic", topic,
                       "--group", f"rp-{int(t0)}", "--flush", str(flush)])
        while time.time() - t0 < 900:
            cur.execute("SELECT coalesce(sum(n), 0) FROM kappa_view")
            if int(cur.fetchone()[0]) >= total:
                break
            time.sleep(0.2)
    else:
        cur.execute("TRUNCATE lambda_batch_view, lambda_speed_view")
        cur.execute("UPDATE lambda_meta SET batch_seq = 0")
        t0 = time.time()
        p, lineas = lanzar(["ingesta/lambda/batch.py", "--interval", "9999"])
        while time.time() - t0 < 900 and not any(RE_CICLO.search(x) for x in list(lineas)):
            time.sleep(0.2)
    dur = time.time() - t0
    detener([p])
    conn.close()
    return round(dur, 2)


def ejecutar(arch, rate, rep, a):
    total = rate * a.duracion
    reset_db()
    ts = int(time.time())
    topic = f"bench-{arch}-{rate}-{rep}-{ts}"
    group = f"{arch}-{ts}"
    crear_topic(topic)
    flush = str(a.flush)

    if arch == "kappa":
        w = [lanzar(["ingesta/kappa/stream.py", "--topic", topic, "--group", group, "--flush", flush])]
        tabla = "kappa_view"
    else:
        w = [lanzar(["ingesta/lambda/speed.py", "--topic", topic, "--group", group, "--flush", flush]),
             lanzar(["ingesta/lambda/batch.py", "--interval", str(a.batch_interval)])]
        tabla = "lambda_serving"

    time.sleep(a.warmup)                      # deja que los consumidores se unan al grupo
    mon = Muestreador([p.pid for p, _ in w]); mon.start()
    son = Sondeo(tabla); son.start()

    t_sent = producir(topic, rate, total, seed=a.seed + rep)

    limite = time.time() + a.duracion * 4 + 30
    while time.time() < limite and not (son.c and son.c[-1] >= total):
        time.sleep(0.2)
    son.parar(); mon.parar()

    tp = np.array(son.t)
    cp = np.maximum.accumulate(np.array(son.c))
    visto = int(cp[-1])
    completado = visto >= total
    idx = np.arange(0, total, max(1, total // 3000))          # muestra de eventos
    pos = np.searchsorted(cp, idx + 1, side="left")           # primer sondeo donde el evento ya es visible
    ok = pos < len(tp)
    lat = np.clip(tp[pos[ok]] - t_sent[idx[ok]], 0, None) if ok.any() else np.array([np.nan])
    t_fin = tp[np.searchsorted(cp, total, side="left")] if completado else tp[-1]
    t_total = t_fin - t_sent[0]
    p50, p95, p99 = np.percentile(lat, [50, 95, 99])

    ciclos = [float(m.group(2)) for _, l in w[1:] for x in list(l) if (m := RE_CICLO.search(x))]
    detener([p for p, _ in w])

    fila = {
        "arch": arch, "rate_objetivo": rate, "rep": rep, "total": total,
        "rate_producido": round(total / (t_sent[-1] - t_sent[0]), 1),
        "completado": completado, "t_total_s": round(t_total, 2),
        "throughput_eps": round(visto / t_total, 1),
        "lat_p50_s": round(p50, 3), "lat_p95_s": round(p95, 3),
        "lat_p99_s": round(p99, 3), "lat_max_s": round(float(lat.max()), 3),
        "cpu_prom_pct": round(float(np.mean(mon.cpu)), 1) if mon.cpu else None,
        "rss_max_mb": round(max(mon.rss) / 1024 ** 2, 1) if mon.rss else None,
        "batch_ciclos": len(ciclos) if arch == "lambda" else None,
        "batch_dur_prom_s": round(float(np.mean(ciclos)), 3) if ciclos else None,
        "batch_dur_max_s": round(max(ciclos), 3) if ciclos else None,
        "reproceso_s": reproceso(arch, topic, total, a.flush) if a.reproceso and completado else None,
        "flush_s": a.flush,
    }
    return fila


def guardar(fila, ruta):
    existe = ruta.exists()
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, CAMPOS)
        if not existe:
            w.writeheader()
        w.writerow(fila)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arch", choices=["kappa", "lambda", "ambas"], default="ambas")
    p.add_argument("--rates", default="500,2000,5000", help="eventos/s, separados por coma")
    p.add_argument("--duracion", type=int, default=30, help="segundos de produccion por corrida")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--flush", type=float, default=1.0)
    p.add_argument("--batch-interval", type=float, default=15.0)
    p.add_argument("--warmup", type=float, default=6.0)
    p.add_argument("--seed", type=int, default=100)
    p.add_argument("--reproceso", action="store_true")
    p.add_argument("--out", default=str(RAIZ / "benchmark" / "resultados" / "ingesta.csv"))
    a = p.parse_args()

    archs = ["kappa", "lambda"] if a.arch == "ambas" else [a.arch]
    ruta = Path(a.out)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    for rate in [int(x) for x in a.rates.split(",")]:
        for rep in range(1, a.reps + 1):
            for arch in archs:
                f = ejecutar(arch, rate, rep, a)
                guardar(f, ruta)
                print(f"[{arch}] {rate} e/s rep {rep}: thr={f['throughput_eps']} e/s, "
                      f"p50={f['lat_p50_s']}s p95={f['lat_p95_s']}s p99={f['lat_p99_s']}s, "
                      f"completado={f['completado']}")


if __name__ == "__main__":
    main()