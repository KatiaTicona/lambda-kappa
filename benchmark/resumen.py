"""Resume los CSV del benchmark en tablas (Markdown) y una figura."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RES = Path(__file__).resolve().parent / "resultados"
COLOR = {"kappa": "#1f77b4", "lambda": "#ff7f0e", "rest": "#2ca02c", "graphql": "#d62728"}


def leer(nombre):
    ruta = RES / nombre
    return pd.read_csv(ruta) if ruta.exists() else None


def fmt(m, s, dec):
    if pd.isna(m):
        return "—"
    return f"{m:.{dec}f} ± {0 if pd.isna(s) else s:.{dec}f}"


def agrega(df, claves, cols):
    """Media ± desviación estándar por grupo. cols = {columna: decimales}."""
    g = df.groupby(claves)
    out = g.size().rename("n").reset_index()
    indice = out.set_index(claves).index
    for c, dec in cols.items():
        m, s = g[c].mean(), g[c].std(ddof=1)
        out[c] = [fmt(m[k], s[k], dec) for k in indice]
    return out


def md(df):
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    filas = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *filas])


def barras(ax, df, x, grupo, y, titulo, xlabel, ylabel, log=False):
    xs = sorted(df[x].unique())
    grupos = list(dict.fromkeys(df[grupo]))
    w = 0.8 / len(grupos)
    for i, nombre in enumerate(grupos):
        sub = df[df[grupo] == nombre].groupby(x)[y]
        m = sub.mean().reindex(xs)
        s = sub.std(ddof=1).reindex(xs).fillna(0)
        pos = np.arange(len(xs)) - 0.4 + w * (i + 0.5)
        ax.bar(pos, m.values, w, yerr=s.values, capsize=3, label=nombre, color=COLOR.get(nombre))
    ax.set_xticks(np.arange(len(xs)))
    ax.set_xticklabels([str(v) for v in xs])
    ax.set_title(titulo, fontsize=9)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=8)
    if log:
        ax.set_yscale("log")
    ax.legend(fontsize=7)


def main():
    ing, rep, api = leer("ingesta.csv"), leer("reproceso.csv"), leer("api.csv")
    partes = ["# Resumen del benchmark", "",
              "Valores: media ± desviación estándar de `n` repeticiones independientes.", ""]

    if ing is not None:
        t = agrega(ing, ["rate_objetivo", "arch"],
                   {"rate_producido": 0, "throughput_eps": 0, "lat_p50_s": 3, "lat_p95_s": 3,
                    "lat_p99_s": 3, "cpu_prom_pct": 1, "rss_max_mb": 0})
        comp = ing.groupby(["rate_objetivo", "arch"])["completado"].sum().reset_index(name="completadas")
        t = t.merge(comp, on=["rate_objetivo", "arch"])
        col = t.pop("completadas")
        t.insert(3, "completadas", col.astype(str) + "/" + t["n"].astype(str))
        partes += ["## Ingesta: Kappa vs Lambda", "",
                   "Latencia = tiempo desde que se produce el evento hasta que es visible en la vista de consulta. "
                   "`completadas` = corridas que procesaron todos los eventos.", "", md(t), ""]

        lam = ing[ing["arch"] == "lambda"]
        if lam["batch_ciclos"].notna().any():
            b = agrega(lam, ["rate_objetivo"],
                       {"batch_ciclos": 1, "batch_dur_prom_s": 3, "batch_dur_max_s": 3})
            partes += ["## Costo de la capa batch (Lambda)", "", md(b), ""]

    if rep is not None and rep["reproceso_s"].notna().any():
        r = agrega(rep.dropna(subset=["reproceso_s"]), ["arch", "total"], {"reproceso_s": 1})
        partes += ["## Reprocesamiento desde cero", "", md(r), ""]

    if api is not None:
        t = agrega(api, ["usuarios", "api"],
                   {"dashboards_s": 1, "lat_p50_ms": 0, "lat_p95_ms": 0, "lat_p99_ms": 0,
                    "bytes_prom": 0, "cpu_prom_pct": 1, "rss_max_mb": 0})
        f = api.groupby(["usuarios", "api"])["fallos"].sum().reset_index(name="fallos_tot")
        partes += ["## API: REST vs GraphQL", "",
                   "Un dashboard = resumen + serie (2 peticiones HTTP en REST, 1 en GraphQL).", "",
                   md(t.merge(f, on=["usuarios", "api"])), ""]

    (RES / "resumen.md").write_text("\n".join(partes), encoding="utf-8")

    fig, axs = plt.subplots(2, 2, figsize=(9, 6.2))
    axs = axs.flatten()
    for ax in axs:
        ax.axis("off")
    if ing is not None:
        axs[0].axis("on")
        barras(axs[0], ing, "rate_objetivo", "arch", "lat_p95_s",
               "Ingesta: latencia p95", "Tasa objetivo (eventos/s)", "segundos (escala log)", log=True)
        axs[1].axis("on")
        barras(axs[1], ing, "rate_objetivo", "arch", "throughput_eps",
               "Ingesta: throughput efectivo", "Tasa objetivo (eventos/s)", "eventos/s")
    if api is not None:
        axs[2].axis("on")
        barras(axs[2], api, "usuarios", "api", "dashboards_s",
               "API: dashboards por segundo", "Usuarios concurrentes", "dashboards/s")
        axs[3].axis("on")
        barras(axs[3], api, "usuarios", "api", "lat_p95_ms",
               "API: latencia p95 del dashboard", "Usuarios concurrentes", "ms (escala log)", log=True)
    fig.tight_layout()
    fig.savefig(RES / "figura_resumen.png", dpi=200)
    print("Generados: resumen.md y figura_resumen.png en", RES)


if __name__ == "__main__":
    main()