import argparse, json, random, time, uuid
from datetime import datetime, timezone
from confluent_kafka import Producer

TIPOS = ["consulta", "tramite", "pago", "reclamo"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rate", type=int, default=1000, help="eventos/s")
    p.add_argument("--total", type=int, default=100000)
    p.add_argument("--topic", default="eventos")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    random.seed(a.seed)
    prod = Producer({"bootstrap.servers": "localhost:9092", "linger.ms": 5})
    inicio = time.time()
    for i in range(a.total):
        ev = {
            "event_id": str(uuid.UUID(int=random.getrandbits(128))),
            "user_id": random.randint(1, 5000),
            "event_type": random.choice(TIPOS),
            "amount": round(random.uniform(1, 500), 2),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        prod.produce(a.topic, json.dumps(ev).encode())
        prod.poll(0)
        pausa = inicio + (i + 1) / a.rate - time.time()
        if pausa > 0:
            time.sleep(pausa)
    prod.flush()
    print(f"Enviados {a.total} eventos en {time.time()-inicio:.1f}s")

if __name__ == "__main__":
    main()