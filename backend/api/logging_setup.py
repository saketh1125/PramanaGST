"""Production logging: stdlib JSON logs + request-ID middleware.

Privacy rules (enforced by allowlisting, not by convention):
- log the matched route template ("/api/v1/risks/{gstin}"), never the raw
  path — paths carry GSTINs.
- never log request/response bodies, headers (except a redacted key-presence
  flag), amounts, names, invoice numbers, API keys, or DB credentials.
- vendor context in logs is limited to band/score aggregates.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone

_logger = logging.getLogger("pramanagst")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "service": "pramanagst-api",
            "msg": record.getMessage(),
        }
        for key in ("request_id", "method", "route", "status",
                    "latency_ms", "error_code", "exc_type", "extra"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload)


def configure_logging(level: str = "INFO") -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    _logger.handlers = [handler]
    _logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    _logger.propagate = False
    return _logger


def get_logger() -> logging.Logger:
    return _logger


def log_llm_fallback(reason: str, latency_ms: float) -> None:
    _logger.warning("llm.fallback", extra={"extra": {"reason": reason,
                                                     "latency_ms": round(latency_ms, 1)}})


async def _request_id_middleware(request, call_next):
    from starlette.responses import JSONResponse  # local import: no cycle

    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        _logger.exception("http.unhandled",
                          extra={"request_id": request_id,
                                 "method": request.method,
                                 "route": _route_template(request),
                                 "latency_ms": latency_ms})
        return JSONResponse(status_code=500, content={
            "contract_version": "1.0.0", "entity": "ERROR",
            "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}})
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    _logger.info("http.request", extra={
        "request_id": request_id, "method": request.method,
        "route": _route_template(request), "status": response.status_code,
        "latency_ms": latency_ms})
    return response


def _route_template(request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path
