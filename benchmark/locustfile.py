import os
import time

from locust import HttpUser, constant, task

API = os.getenv("API", "rest")
FUENTE = os.getenv("FUENTE", "kappa")
MINUTOS = int(os.getenv("MINUTOS", "60"))

GQL = ('{ resumen(fuente: "%s") { eventType eventos monto } '
       'serie(fuente: "%s", tipo: "pago", minutos: %d) { minute eventos } }') % (FUENTE, FUENTE, MINUTOS)


class Usuario(HttpUser):
    wait_time = constant(0)

    @task
    def dashboard(self):
        t0 = time.perf_counter()
        exc = None
        largo = 0
        try:
            if API == "rest":
                urls = [f"/resumen?fuente={FUENTE}",
                        f"/serie?fuente={FUENTE}&tipo=pago&minutos={MINUTOS}"]
                for url in urls:
                    with self.client.get(url, name=url.split("?")[0], catch_response=True) as r:
                        largo += len(r.content)
                        if r.status_code != 200:
                            r.failure(f"HTTP {r.status_code}")
                            exc = Exception(f"HTTP {r.status_code}")
            else:
                with self.client.post("/graphql", json={"query": GQL},
                                      name="/graphql", catch_response=True) as r:
                    largo += len(r.content)
                    if r.status_code != 200 or "errors" in r.json():
                        r.failure("error GraphQL")
                        exc = Exception("error GraphQL")
        except Exception as e:
            exc = e
        self.environment.events.request.fire(
            request_type="TAREA", name="dashboard",
            response_time=(time.perf_counter() - t0) * 1000,
            response_length=largo, exception=exc, context={},
        )