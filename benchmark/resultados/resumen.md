# Resumen del benchmark

Valores: media ± desviación estándar de `n` repeticiones independientes.

## Ingesta: Kappa vs Lambda

Latencia = tiempo desde que se produce el evento hasta que es visible en la vista de consulta. `completadas` = corridas que procesaron todos los eventos.

| rate_objetivo | arch | n | completadas | rate_producido | throughput_eps | lat_p50_s | lat_p95_s | lat_p99_s | cpu_prom_pct | rss_max_mb |
|---|---|---|---|---|---|---|---|---|---|---|
| 500 | kappa | 6 | 6/6 | 500 ± 0 | 491 ± 4 | 0.634 ± 0.028 | 1.094 ± 0.035 | 1.161 ± 0.035 | 0.0 ± 0.0 | 3 ± 0 |
| 500 | lambda | 6 | 6/6 | 500 ± 0 | 486 ± 5 | 0.724 ± 0.036 | 1.208 ± 0.042 | 1.278 ± 0.040 | 0.0 ± 0.0 | 7 ± 0 |
| 2000 | kappa | 6 | 6/6 | 2000 ± 0 | 1964 ± 28 | 0.613 ± 0.016 | 1.064 ± 0.016 | 1.136 ± 0.014 | 0.0 ± 0.0 | 3 ± 0 |
| 2000 | lambda | 6 | 6/6 | 2000 ± 0 | 1967 ± 11 | 0.796 ± 0.053 | 1.256 ± 0.052 | 1.370 ± 0.067 | 0.0 ± 0.0 | 7 ± 0 |
| 5000 | kappa | 6 | 6/6 | 5000 ± 0 | 4877 ± 16 | 0.293 ± 0.010 | 0.494 ± 0.012 | 0.846 ± 0.101 | 0.0 ± 0.0 | 3 ± 0 |
| 5000 | lambda | 6 | 6/6 | 5000 ± 0 | 4817 ± 25 | 0.497 ± 0.064 | 0.749 ± 0.093 | 1.241 ± 0.157 | 0.0 ± 0.0 | 6 ± 0 |

## Costo de la capa batch (Lambda)

| rate_objetivo | n | batch_ciclos | batch_dur_prom_s | batch_dur_max_s |
|---|---|---|---|---|
| 500 | 6 | 2.0 ± 0.0 | 0.062 ± 0.031 | 0.080 ± 0.057 |
| 2000 | 6 | 2.0 ± 0.0 | 0.131 ± 0.050 | 0.150 ± 0.066 |
| 5000 | 6 | 2.0 ± 0.0 | 0.282 ± 0.114 | 0.337 ± 0.123 |

## API: REST vs GraphQL

Un dashboard = resumen + serie (2 peticiones HTTP en REST, 1 en GraphQL).

| usuarios | api | n | dashboards_s | lat_p50_ms | lat_p95_ms | lat_p99_ms | bytes_prom | cpu_prom_pct | rss_max_mb | fallos_tot |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | graphql | 3 | 20.2 ± 0.9 | 467 ± 21 | 673 ± 40 | 3067 ± 153 | 379 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
| 10 | rest | 3 | 29.9 ± 2.0 | 280 ± 20 | 523 ± 42 | 950 ± 260 | 667 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
| 50 | graphql | 3 | 35.3 ± 1.6 | 1200 ± 0 | 2433 ± 289 | 5033 ± 58 | 379 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
| 50 | rest | 3 | 37.6 ± 4.9 | 1093 ± 110 | 2433 ± 351 | 5100 ± 361 | 667 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
| 200 | graphql | 3 | 27.2 ± 3.5 | 6367 ± 1124 | 11967 ± 1790 | 13333 ± 2082 | 379 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
| 200 | rest | 3 | 44.8 ± 1.3 | 3667 ± 58 | 8700 ± 700 | 9400 ± 557 | 667 ± 0 | 0.0 ± 0.0 | 3 ± 0 | 0 |
