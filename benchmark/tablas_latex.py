"""Genera tablas LaTeX (booktabs) desde los CSV y copia la figura a informe/."""
import shutil
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "benchmark" / "resultados"
OUT = RAIZ / "informe"
NOMBRE = {"kappa": "Kappa", "lambda": "Lambda", "rest": "REST", "graphql": "GraphQL"}


def pm(m, s, dec):
    s = 0.0 if pd.isna(s) else s
    return f"${m:.{dec}f}\\pm{s:.{dec}f}$"


def construir(df, k1, k2, spec, cabecera, columnas, extra):
    nombres = [c for c, _ in columnas]
    g = df.groupby([k1, k2])
    med, sd, n = g[nombres].mean(), g[nombres].std(ddof=1), g.size()
    filas, previo = [], None
    for idx in med.index:
        a, b = idx
        primera = a != previo
        if previo is not None and primera:
            filas.append(r"\midrule")
        previo = a
        celdas = [f"{a:,}".replace(",", r"\,") if primera else "", NOMBRE.get(b, b)]
        celdas += [pm(med.loc[idx, c], sd.loc[idx, c], d) for c, d in columnas]
        celdas.append(extra(df, idx, n[idx]))
        filas.append(" & ".join(celdas) + r" \\")
    return "\n".join([rf"\begin{{tabular}}{{{spec}}}", r"\toprule", cabecera + r" \\",
                      r"\midrule", *filas, r"\bottomrule", r"\end{tabular}"])


def completadas(df, idx, n):
    sub = df[(df["rate_objetivo"] == idx[0]) & (df["arch"] == idx[1])]
    return f"{n}"


def fallos(df, idx, n):
    sub = df[(df["usuarios"] == idx[0]) & (df["api"] == idx[1])]
    return str(int(sub["fallos"].sum()))


def main():
    OUT.mkdir(exist_ok=True)
    ing = pd.read_csv(RES / "ingesta.csv")
    api = pd.read_csv(RES / "api.csv")

    t1 = construir(
        ing, "rate_objetivo", "arch", "rlrrrrrrr",
        r"Tasa (e/s) & Arq. & Throughput (e/s) & p50 (s) & p95 (s) & p99 (s) & CPU (\%) & RAM (MB) & n",
        [("throughput_eps", 0), ("lat_p50_s", 2), ("lat_p95_s", 2), ("lat_p99_s", 2),
         ("cpu_prom_pct", 1), ("rss_max_mb", 0)],
        completadas)
    t2 = construir(
        api, "usuarios", "api", "rlrrrrrr",
        r"Usuarios & API & Dashboards/s & p50 (ms) & p95 (ms) & p99 (ms) & Bytes & Fallos",
        [("dashboards_s", 1), ("lat_p50_ms", 0), ("lat_p95_ms", 0), ("lat_p99_ms", 0),
         ("bytes_prom", 0)],
        fallos)
    (OUT / "tabla_ingesta.tex").write_text(t1, encoding="utf-8")
    (OUT / "tabla_api.tex").write_text(t2, encoding="utf-8")

    fig = RES / "figura_resumen.png"
    if fig.exists():
        shutil.copy(fig, OUT / "figura_resumen.png")
    print("Listo: tablas y figura en", OUT)


if __name__ == "__main__":
    main()