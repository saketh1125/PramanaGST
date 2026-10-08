"""
PramanaGST API layer — thin orchestration over ingestion, graph,
reconciliation and risk services.

Endpoints follow Contracts 2–5. Risk detail/explain are Contract 4;
risk-summary, the flattened vendor list, the error envelope, and graph
view models are Contract 5 projections. Contract 5 models live in
backend/api/models. Auth is out of scope; the analytics context is
built once per process; set PRAMANAGST_USE_NEO4J=1 to serve projections
from a live Neo4j instead of the offline batch path.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.graph.builder.projection import build_from_batch, project_from_neo4j
from backend.ingestion.ingest_service import IngestService
from backend.reconciliation.engine.matcher import reconcile
from backend.reconciliation.engine.models import ReconReport
from backend.risk_ai.explainability.narrator import narrate
from backend.risk_ai.models.contract4 import AuditNarrativeResponse
from backend.api.models.contract5 import (
    GraphLink,
    GraphNode,
    GraphView,
    RiskSummary,
    VendorRiskView,
)
from backend.risk_ai.models.vendor_risk import VendorRisk, score_vendors

DATA_DIR = os.path.join("backend", "ingestion", "dataset", "generated_data")

app = FastAPI(
    title="PramanaGST API",
    description="Intelligent GST reconciliation over a knowledge graph.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class _Analytics:
    """Lazily-built, process-wide analytics snapshot."""

    def __init__(self):
        self._batch = None
        self._graph = None
        self._recon = None
        self._vendors = None

    def invalidate(self):
        self.__init__()

    @property
    def batch(self) -> dict:
        if self._batch is None:
            self._batch = IngestService(DATA_DIR).process()
        return self._batch

    @property
    def graph(self):
        if self._graph is None:
            if os.environ.get("PRAMANAGST_USE_NEO4J"):
                try:
                    self._graph = project_from_neo4j()
                except Exception as exc:
                    raise ApiError(503, "SERVICE_UNAVAILABLE", f"Neo4j unavailable: {exc}")
            else:
                self._graph = build_from_batch(self.batch)
        return self._graph

    @property
    def recon(self) -> ReconReport:
        if self._recon is None:
            raw = reconcile(self.graph)
            self._recon = ReconReport(summary=raw["summary"], items=raw["items"])
        return self._recon

    @property
    def vendors(self) -> list[VendorRisk]:
        if self._vendors is None:
            raw_recon = {"summary": self.recon.summary.model_dump(by_alias=True),
                         "items": [i.model_dump(by_alias=True) for i in self.recon.items]}
            self._vendors = score_vendors(self.graph, raw_recon)
        return self._vendors


_ctx = _Analytics()


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def _vendor_or_404(gstin: str) -> VendorRisk:
    for v in _ctx.vendors:
        if v.gstin == gstin:
            return v
    raise ApiError(404, "VENDOR_NOT_FOUND", f"Vendor {gstin} not found")


def _vendor_view(v: VendorRisk) -> VendorRiskView:
    return VendorRiskView(
        gstin=v.gstin,
        legalName=v.legal_name,
        score=v.score,
        band=v.band,
        reasons=v.reasons,
        invoicesIssued=v.signals.invoices_issued,
    )


_ERROR_META = {"contract_version": "1.0.0", "entity": "ERROR"}


def _error_body(code: str, message: str) -> dict:
    return {**_ERROR_META, "error": {"code": code, "message": message}}


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code,
                        content=_error_body(exc.code, exc.detail))


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    code = getattr(exc, "code", "HTTP_ERROR")
    return JSONResponse(status_code=exc.status_code,
                        content=_error_body(code, str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    message = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    return JSONResponse(status_code=422,
                        content=_error_body("VALIDATION_ERROR", message))


@app.exception_handler(StarletteHTTPException)
async def starlette_http_error_handler(request: Request, exc: StarletteHTTPException):
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    message = "Route not found" if exc.status_code == 404 and exc.detail == "Not Found" else str(exc.detail)
    return JSONResponse(status_code=exc.status_code,
                        content=_error_body(code, message))


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500,
                        content=_error_body("INTERNAL_ERROR", "Internal server error"))


# --- Contract 1 surface -------------------------------------------------------

@app.post("/api/v1/ingest", tags=["ingestion"])
def ingest(persist: bool = False):
    """Run the ingestion pipeline; optionally persist to Neo4j."""
    batch = IngestService(DATA_DIR).process()
    result = {"metadata": batch["batch_metadata"]}
    if persist:
        try:
            from backend.graph.builder.loader import Neo4jLoader

            with Neo4jLoader() as loader:
                loader.apply_schema()
                result["persisted"] = loader.load_batch(batch)
        except Exception as exc:
            raise ApiError(503, "SERVICE_UNAVAILABLE", f"Neo4j unavailable: {exc}")
        _ctx.invalidate()
    return result


# --- Contract 2 surface -------------------------------------------------------

@app.get("/api/v1/reconciliation", response_model=ReconReport, tags=["reconciliation"])
def reconciliation():
    return _ctx.recon


@app.get("/api/v1/reconciliation/{gstin}", response_model=ReconReport, tags=["reconciliation"])
def reconciliation_for(gstin: str):
    raw = reconcile(_ctx.graph, gstin=gstin)
    return ReconReport(summary=raw["summary"], items=raw["items"])


# --- Contract 4 surface (Risk AI -> API) -------------------------------------
# Risk detail and explain are Contract 4; risk-summary and the flattened
# vendor list below are Contract 5 projections of the same data.

@app.get("/api/v1/risks/{gstin}", response_model=VendorRisk, tags=["risk"],
         summary="Contract 4: vendor risk detail")
def risk_for(gstin: str):
    return _vendor_or_404(gstin)


@app.get("/api/v1/risks/{gstin}/explain", response_model=AuditNarrativeResponse, tags=["risk"],
         summary="Contract 4: audit narrative")
def explain(gstin: str):
    return AuditNarrativeResponse(gstin=gstin, narrative=narrate(_vendor_or_404(gstin)))


# --- Contract 5 surface (API -> Dashboard) ------------------------------------

@app.get("/api/v1/risk-summary", response_model=RiskSummary, tags=["risk"])
def risk_summary():
    vendors = _ctx.vendors
    high = sum(1 for v in vendors if v.band == "HIGH")
    medium = sum(1 for v in vendors if v.band == "MEDIUM")
    low = sum(1 for v in vendors if v.band == "LOW")
    avg = round(sum(v.score for v in vendors) / len(vendors), 2) if vendors else 0.0
    return RiskSummary(
        totalVendors=len(vendors),
        highRisk=high,
        mediumRisk=medium,
        lowRisk=low,
        averageScore=avg,
    )


@app.get("/api/v1/risks", response_model=list[VendorRiskView], tags=["risk"])
def risks(band: str | None = None, minScore: float | None = None):
    vendors = _ctx.vendors
    if band is not None:
        band = band.upper()
        if band not in ("HIGH", "MEDIUM", "LOW"):
            raise ApiError(422, "VALIDATION_ERROR", f"band must be HIGH/MEDIUM/LOW, got {band}")
        vendors = [v for v in vendors if v.band == band]
    if minScore is not None:
        vendors = [v for v in vendors if v.score >= minScore]
    return [_vendor_view(v) for v in vendors]


@app.get("/api/v1/graph/ego/{gstin}", response_model=GraphView, tags=["graph"])
def ego_graph(gstin: str, depth: int = 1):
    """Subgraph around a taxpayer for force-directed rendering."""
    g = _ctx.graph
    key = f"Taxpayer:{gstin}"
    if key not in g:
        raise ApiError(404, "TAXPAYER_NOT_FOUND", f"Taxpayer {gstin} not found")

    frontier = {key}
    for _ in range(max(1, min(depth, 3))):  # cap depth at 3
        nxt = set()
        for n in frontier:
            nxt |= set(g.predecessors(n)) | set(g.successors(n))
        frontier |= nxt

    sub = g.subgraph(frontier)
    nodes = [
        GraphNode(
            id=n,
            label=str(d.get("label") or n.split(":", 1)[0]),
            legalName=d["legalName"] if isinstance(d.get("legalName"), str) else None,
            invoiceNumber=d["invoiceNumber"] if isinstance(d.get("invoiceNumber"), str) else None,
            returnId=d["returnId"] if isinstance(d.get("returnId"), str) else None,
        )
        for n, d in sub.nodes(data=True)
    ]
    links = [
        GraphLink(source=u, target=v, type=d["type"] if isinstance(d.get("type"), str) else None)
        for u, v, d in sub.edges(data=True)
    ]
    return GraphView(nodes=nodes, links=links)


@app.get("/api/v1/health", tags=["system"])
def health():
    return {"status": "ok", "neo4j_mode": bool(os.environ.get("PRAMANAGST_USE_NEO4J"))}
