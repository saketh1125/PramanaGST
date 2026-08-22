"""
PramanaGST API layer — thin orchestration over ingestion, graph,
reconciliation and risk services.

Endpoints follow Contracts 2–4. The analytics context is built once per
process; set PRAMANAGST_USE_NEO4J=1 to serve projections from a live
Neo4j instead of the offline batch path.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.graph.builder.projection import build_from_batch, project_from_neo4j
from backend.ingestion.ingest_service import IngestService
from backend.reconciliation.engine.matcher import reconcile
from backend.reconciliation.engine.models import ReconReport
from backend.risk_ai.explainability.narrator import narrate
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
                    raise HTTPException(503, f"Neo4j unavailable: {exc}")
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


def _vendor_or_404(gstin: str) -> VendorRisk:
    for v in _ctx.vendors:
        if v.gstin == gstin:
            return v
    raise HTTPException(404, f"Vendor {gstin} not found")


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
            raise HTTPException(503, f"Neo4j unavailable: {exc}")
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


# --- Contract 3 surface -------------------------------------------------------

@app.get("/api/v1/risks", response_model=list[VendorRisk], tags=["risk"])
def risks():
    return _ctx.vendors


@app.get("/api/v1/risks/{gstin}", response_model=VendorRisk, tags=["risk"])
def risk_for(gstin: str):
    return _vendor_or_404(gstin)


@app.get("/api/v1/risks/{gstin}/explain", tags=["risk"])
def explain(gstin: str):
    return {"gstin": gstin, "narrative": narrate(_vendor_or_404(gstin))}


# --- Graph visualization surface ---------------------------------------------

@app.get("/api/v1/graph/ego/{gstin}", tags=["graph"])
def ego_graph(gstin: str, depth: int = 1):
    """Subgraph around a taxpayer for force-directed rendering."""
    g = _ctx.graph
    key = f"Taxpayer:{gstin}"
    if key not in g:
        raise HTTPException(404, f"Taxpayer {gstin} not found")

    frontier = {key}
    for _ in range(max(1, min(depth, 3))):  # cap depth at 3
        nxt = set()
        for n in frontier:
            nxt |= set(g.predecessors(n)) | set(g.successors(n))
        frontier |= nxt

    sub = g.subgraph(frontier)
    return {
        "nodes": [
            {"id": n, **{k: v for k, v in d.items() if isinstance(v, (str, int, float, bool))}}
            for n, d in sub.nodes(data=True)
        ],
        "links": [
            {"source": u, "target": v, **d}
            for u, v, d in sub.edges(data=True)
        ],
    }


@app.get("/api/v1/health", tags=["system"])
def health():
    return {"status": "ok", "neo4j_mode": bool(os.environ.get("PRAMANAGST_USE_NEO4J"))}
