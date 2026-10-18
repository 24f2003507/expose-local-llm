
import os
import time
import json
import uuid
from datetime import datetime, timezone
from collections import deque

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

EMAIL = "24f2003507@ds.study.iitm.ac.in"
START_TIME = time.monotonic()

# Prometheus exports this counter as http_requests_total.
REQUEST_COUNT = Counter(
    "http_requests",
    "Total number of HTTP requests received"
)

# Keep the most recent 1000 log entries in memory.
LOGS = deque(maxlen=1000)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # Count every request, including requests to /metrics.
    REQUEST_COUNT.inc()

    try:
        response = await call_next(request)
        level = "INFO"
    except Exception:
        level = "ERROR"
        raise
    finally:
        LOGS.append({
            "level": level,
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id
        })

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def home():
    return {"status": "Observability API is running"}


@app.get("/work")
def work(n: int = 1):
    if n < 0:
        return Response(
            content=json.dumps({"detail": "n must be non-negative"}),
            status_code=400,
            media_type="application/json"
        )

    # Perform K units of simple work.
    result = 0
    for i in range(n):
        result += i

    return {"email": EMAIL, "done": n}


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_s": float(time.monotonic() - START_TIME)
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    limit = max(0, min(limit, 1000))
    return list(LOGS)[-limit:] if limit else []
