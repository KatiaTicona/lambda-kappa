import pandas as pd
from pathlib import Path

RES = Path(__file__).resolve().parent / "resultados"
lo = pd.read_csv(RES / "api.csv")
jm = pd.read_csv(RES / "jmeter" / "jmeter_api.csv")
cols = ["dashboards_s", "lat_p95_ms", "bytes_prom"]

t = (lo.groupby(["usuarios", "api"])[cols].mean().add_suffix("_locust")
     .join(jm.groupby(["usuarios", "api"])[cols].mean().add_suffix("_jmeter")))
t["razon_rps_jmeter/locust"] = t["dashboards_s_jmeter"] / t["dashboards_s_locust"]
print(t.round(2).to_string())

print("\n¿Coincide qué API atiende más dashboards/s?")
for u in sorted(lo["usuarios"].unique()):
    gl = t.loc[(u, "rest"), "dashboards_s_locust"] > t.loc[(u, "graphql"), "dashboards_s_locust"]
    gj = t.loc[(u, "rest"), "dashboards_s_jmeter"] > t.loc[(u, "graphql"), "dashboards_s_jmeter"]
    print(f"{u:>4} usuarios: Locust -> {'REST' if gl else 'GraphQL'} | JMeter -> {'REST' if gj else 'GraphQL'}"
          f" | {'coincide' if gl == gj else 'NO coincide'}")

t.round(2).to_csv(RES / "comparacion_locust_jmeter.csv")