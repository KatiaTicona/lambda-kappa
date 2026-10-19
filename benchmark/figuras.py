"""Genera figuras individuales (una por resultado) para el informe."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "benchmark" / "resultados"
OUT = RAIZ / "informe"
NOMBRE = {"kappa": "Kappa", "lambda": "Lambda", "rest": "REST", "graphql": "GraphQL"}
COLOR = {"kappa": "#1f77b4", "lambda": "#ff7f0e", "rest": "#2ca02c", "graphql": "#d62728"}

plt.rcParams.update({
    "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False,
})


def barras(ax, df, x, grupo, y, ylabel, xlabel, log=False, rot=0):
    xs = sorted(df[x].unique())
    grupos = list(dict.fromkeys(df[grupo]))
    w = 0.8 / len(grupos)
    for i, g in enumerate(grupos):
        s = df[df[grupo] == g].groupby(x)[y]
        m = s.mean().reindex(xs)
        d = s.std(ddof=1).reindex(xs).fillna(0)
        pos = np.arange(len(xs)) - 0.4 + w * (i + 0.5)
        ax.bar(pos, m.values, w, yerr=d.values, capsize=2, label=NOMBRE.get(g, g),
               color=COLOR.get(g), error_kw={"elinewidth": 0.6})
    ax.set_xticks(np.arange(len(xs)))
    ax.set_xticklabels([f"{v:,}" for v in xs])
    ax.tick_params(axis="x", labelrotation=rot)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("log")


def guardar(fig, nombre):
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / nombre, dpi=300)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    ing = pd.read_csv(RES / "ingesta.csv")
    api = pd.read_csv(RES / "api.csv")

    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    barras(ax, ing, "rate_objetivo", "arch", "lat_p95_s", "Latencia p95 (s, escala log)", "Tasa de eventos (e/s)", log=True)
    ax.legend(frameon=False)
    guardar(fig, "fig_ingesta_latencia.png")

    fig, axs = plt.subplots(1, 2, figsize=(3.4, 2.1))
    barras(axs[0], ing, "rate_objetivo", "arch", "cpu_prom_pct", "CPU (% de un núcleo)", "Tasa (e/s)", rot=45)
    barras(axs[1], ing, "rate_objetivo", "arch", "rss_max_mb", "Memoria RSS (MB)", "Tasa (e/s)", rot=45)
    axs[0].legend(frameon=False)
    guardar(fig, "fig_ingesta_recursos.png")

    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    barras(ax, api, "usuarios", "api", "dashboards_s", "Dashboards por segundo", "Usuarios concurrentes")
    ax.legend(frameon=False)
    guardar(fig, "fig_api_rps.png")

    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    barras(ax, api, "usuarios", "api", "lat_p95_ms", "Latencia p95 (ms, escala log)",
           "Usuarios concurrentes", log=True)
    ax.legend(frameon=False)
    guardar(fig, "fig_api_latencia.png")

    print("Listo: 4 figuras en", OUT)


if __name__ == "__main__":
    main()