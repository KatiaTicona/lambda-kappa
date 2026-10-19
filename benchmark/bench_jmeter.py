"""Benchmark de APIs con Apache JMeter (modo no-GUI) para verificar los resultados de Locust."""
import argparse, csv, shutil, subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.bench_api import APIS, listo
from benchmark.bench_ingesta import RAIZ, Muestreador, detener, lanzar

JM = RAIZ / "benchmark" / "jmeter"
RES = RAIZ / "benchmark" / "resultados" / "jmeter"
CAMPOS = ["api", "usuarios", "rep", "fuente", "solicitudes", "fallos", "dashboards_s",
          "lat_media_ms", "lat_p50_ms", "lat_p95_ms", "lat_p99_ms", "bytes_prom",
          "cpu_prom_pct", "rss_max_mb"]


def analizar(jtl, descarte):
    d = pd.read_csv(jtl)
    d = d[d["label"] == "dashboard"].copy()
    d = d[d["timeStamp"] >= d["timeStamp"].min() + descarte * 1000]      # sin calentamiento
    ventana = ((d["timeStamp"] + d["elapsed"]).max() - d["timeStamp"].min()) / 1000
    ok = d["success"].astype(str).str.lower() == "true"
    return {
        "solicitudes": len(d), "fallos": int((~ok).sum()),
        "dashboards_s": round(len(d) / ventana, 1),
        "lat_media_ms": round(float(d["elapsed"].mean()), 1),
        "lat_p50_ms": float(np.percentile(d["elapsed"], 50)),
        "lat_p95_ms": float(np.percentile(d["elapsed"], 95)),
        "lat_p99_ms": float(np.percentile(d["elapsed"], 99)),
        "bytes_prom": round(float(d["bytes"].mean()), 1),
    }


def ejecutar(api, usuarios, rep, a, exe):
    modulo, puerto = APIS[api]
    base = f"{api}_u{usuarios}_r{rep}"
    jtl = RES / "jtl" / f"{base}.jtl"
    html = RES / "html" / base
    jtl.parent.mkdir(parents=True, exist_ok=True)
    html.parent.mkdir(parents=True, exist_ok=True)
    if jtl.exists():
        jtl.unlink()
    if html.exists():
        shutil.rmtree(html)

    srv, _ = lanzar(["-m", "uvicorn", modulo, "--port", str(puerto), "--log-level", "warning"])
    try:
        if not listo(api, puerto):
            raise RuntimeError(f"la API {api} no arranco")
        mon = Muestreador([srv.pid]); mon.start()
        cmd = [exe, "-n", "-t", str(JM / f"{api}.jmx"), "-l", str(jtl),
               f"-Jusers={usuarios}", f"-Jduration={a.duracion}", f"-Jfuente={a.fuente}", "-Jminutos=60"]
        if rep == 1:                                   # reporte HTML solo de la 1.a repeticion
            cmd += ["-e", "-o", str(html)]
        res = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
        mon.parar()
    finally:
        detener([srv])

    if not jtl.exists():
        raise RuntimeError("JMeter no genero resultados:\n" + (res.stdout + res.stderr)[-1500:])
    fila = {"api": api, "usuarios": usuarios, "rep": rep, "fuente": a.fuente,
            **analizar(jtl, a.descarte),
            "cpu_prom_pct": round(float(np.mean(mon.cpu)), 1) if mon.cpu else None,
            "rss_max_mb": round(max(mon.rss) / 1024 ** 2, 1) if mon.rss else None}
    return fila


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--usuarios", default="10,50,200")
    p.add_argument("--duracion", type=int, default=40)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--fuente", choices=["kappa", "lambda"], default="kappa")
    p.add_argument("--descarte", type=float, default=5.0, help="segundos iniciales descartados")
    p.add_argument("--jmeter", default="jmeter")
    p.add_argument("--out", default=str(RES / "jmeter_api.csv"))
    a = p.parse_args()

    exe = shutil.which(a.jmeter)
    if exe is None:
        raise SystemExit("No se encuentra JMeter: agrega su carpeta bin al PATH o usa --jmeter RUTA\\jmeter.bat")

    ruta = Path(a.out)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    for u in [int(x) for x in a.usuarios.split(",")]:
        for rep in range(1, a.reps + 1):
            for api in ("rest", "graphql"):
                f = ejecutar(api, u, rep, a, exe)
                existe = ruta.exists()
                with open(ruta, "a", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, CAMPOS)
                    if not existe:
                        w.writeheader()
                    w.writerow(f)
                print(f"[JMeter {api}] {u} usuarios rep {rep}: {f['dashboards_s']} dashboards/s, "
                      f"p95={f['lat_p95_ms']} ms, fallos={f['fallos']}, bytes={f['bytes_prom']}")


if __name__ == "__main__":
    main()