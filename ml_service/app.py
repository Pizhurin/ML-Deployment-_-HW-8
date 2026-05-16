"""
ML Service с экспортом метрик для Prometheus.
SLO:
  - Latency p95 < 1s
  - Error Rate < 1%
  - Availability > 99%
"""
import time
import random
import os
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Histogram, Counter, Gauge,
    generate_latest, CONTENT_TYPE_LATEST
)
import uvicorn

app = FastAPI(title="ML Service")

# ── Метрики Prometheus ─────────────────────────────────────────────────────────

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0]
)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of active requests being processed"
)

MODEL_PREDICTION_ERRORS = Counter(
    "model_prediction_errors_total",
    "Total number of model prediction errors"
)

# ── Режим искусственной задержки (для проверки алерта) ─────────────────────────
SLOW_MODE = os.getenv("SLOW_MODE", "false").lower() == "true"


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    ACTIVE_REQUESTS.inc()
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    REQUEST_LATENCY.observe(latency)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    ACTIVE_REQUESTS.dec()
    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/predict")
def predict(feature: float = 1.0):
    """Имитация ML-предсказания."""
    if SLOW_MODE:
        time.sleep(2.0)   # искусственная задержка для триггера алерта
    else:
        time.sleep(random.uniform(0.05, 0.3))

    # Случайная ошибка модели с вероятностью 0.5% (в норме < 1%)
    if random.random() < 0.005:
        MODEL_PREDICTION_ERRORS.inc()
        return {"error": "model inference failed"}, 500

    result = feature * 2.0 + random.gauss(0, 0.1)
    return {"prediction": round(result, 4)}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
