import argparse, csv, json, os, subprocess, time, urllib.request
from pathlib import Path

import numpy as np

from benchmark.bench_ingesta import PY, RAIZ, Muestreador, detener, lanzar

APIS = {"rest": ("api.rest.main:app", 8000), "graphql": ("api.graphql.main:app", 8001)}
CAMPOS = ["api", "usuarios", "rep", "fuente", "http_por_dashboard", "solicitudes", "fallos",
          "dashboards_s", "lat_media_ms", "lat_p50_ms", "lat_p95_ms", "lat_p99_ms",
          "bytes_prom", "cpu_prom_pct", "rss_max_mb"]


def listo(api, puerto):
    if api == "rest":
        req = urllib.request.Request(f"http://localhost:{puerto}/health")
    else:
        req = urllib.request.Request(
            f"http://localhost:{puerto}/graphql",
            data=json.dumps({"query": "{ __typename }"}).encode(),
            headers={"Content-Type": "application/json"})
    fin = time.time() + 30
    while time.time() < fin:
        try:
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def ejecutar(api, usuarios, rep, a):
    modulo, puerto = APIS[api]
    prefijo = RAIZ / "benchmark" / "resultados" / "tmp_locust" / f"{api}_{usuarios}_{rep}"
    prefijo.parent.mkdir(parents=True, exist_ok=True)
    srv, _ = lanzar(["-m", "uvicorn", modulo, "--port", str(puerto), "--log-level", "warning"])
    try:
        if not listo(api, puerto):
            raise RuntimeError(f"la API {api} no arranco")
        mon = Muestreador([srv.pid]); mon.start()
        env = dict(os.environ, API=api, FUENTE=a.fuente, MINUTOS="60")
        res = subprocess.run(
            [PY, "-m", "locust", "-f", "benchmark/locustfile.py", "--headless",
             "-u", str(usuarios), "-r", str(usuarios), "-t", f"{a.duracion}s",
             "--reset-stats", "--only-summary", "--csv", str(prefijo),
             "--host", f"http://localhost:{puerto}"],
            cwd=RAIZ, env=env, capture_output=True, text=True)
        mon.parar()
    finally:
        detener([srv])

    ruta_csv = Path(f"{prefijo}_stats.csv")
    if not ruta_csv.exists():
        raise RuntimeError("Locust no genero resultados:\n" + res.stderr[-1500:])
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        r = next(x for x in csv.DictReader(f) if x["Name"] == "dashboard")
    return {
        "api": api, "usuarios": usuarios, "rep": rep, "fuente": a.fuente,
        "http_por_dashboard": 2 if api == "rest" else 1,
        "solicitudes": int(r["Request Count"]), "fallos": int(r["Failure Count"]),
        "dashboards_s": round(float(r["Requests/s"]), 1),
        "lat_media_ms": round(float(r["Average Response Time"]), 1),
        "lat_p50_ms": float(r["50%"]), "lat_p95_ms": float(r["95%"]), "lat_p99_ms": float(r["99%"]),
        "bytes_prom": round(float(r["Average Content Size"]), 1),
        "cpu_prom_pct": round(float(np.mean(mon.cpu)), 1) if mon.cpu else None,
        "rss_max_mb": round(max(mon.rss) / 1024 ** 2, 1) if mon.rss else None,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--usuarios", default="10,50,200")
    p.add_argument("--duracion", type=int, default=40)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--fuente", choices=["kappa", "lambda"], default="kappa")
    p.add_argument("--out", default=str(RAIZ / "benchmark" / "resultados" / "api.csv"))
    a = p.parse_args()

    ruta = Path(a.out)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    for u in [int(x) for x in a.usuarios.split(",")]:
        for rep in range(1, a.reps + 1):
            for api in ("rest", "graphql"):
                fila = ejecutar(api, u, rep, a)
                existe = ruta.exists()
                with open(ruta, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, CAMPOS)
                    if not existe:
                        w.writeheader()
                    w.writerow(fila)
                print(f"[{api}] {u} usuarios rep {rep}: {fila['dashboards_s']} dashboards/s, "
                      f"p95={fila['lat_p95_ms']} ms, fallos={fila['fallos']}, bytes={fila['bytes_prom']}")


if __name__ == "__main__":
    main()