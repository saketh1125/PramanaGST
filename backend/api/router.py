from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.graph.connection import db
from backend.reconciliation import matcher
from backend.risk import composite_scorer

router = APIRouter()

# --- Graph APIs ---

@router.get("/graph/stats")
def get_graph_stats():
    """
    Returns counts of nodes and relationships across the whole graph.
    """
    Q = """
    CALL { MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count }
    WITH collect({label: label, count: count}) AS nodes
    CALL { MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count }
    WITH nodes, collect({type: type, count: count}) AS relationships
    RETURN nodes, relationships
    """
    try:
        with db.get_session() as session:
            result = list(session.run(Q))
            if not result:
                return {"nodes": [], "relationships": []}
            return {
                "nodes": {row['label']: row['count'] for row in result[0]['nodes']},
                "relationships": {row['type']: row['count'] for row in result[0]['relationships']}
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.get("/graph/subgraph/{gstin}")
def get_vendor_subgraph(gstin: str):
    """
    Returns nodes and edges directly connected to a given Taxpayer GSTIN.
    """
    Q = """
    MATCH (t:Taxpayer {gstin: $gstin})-[r]-(n)
    RETURN t, r, n LIMIT 200
    """
    nodes = {}
    edges = []
    
    try:
        with db.get_session() as session:
            for record in session.run(Q, gstin=gstin):
                t_node = record["t"]
                n_node = record["n"]
                r_rel = record["r"]
                
                # Deduplicate nodes via dictionary
                for node in [t_node, n_node]:
                    nodes[node.id] = {
                        "id": str(node.id),
                        "label": list(node.labels)[0],
                        "properties": dict(node)
                    }
                    
                edges.append({
                    "id": f"{r_rel.start_node.id}-{r_rel.type}-{r_rel.end_node.id}",
                    "source": str(r_rel.start_node.id),
                    "target": str(r_rel.end_node.id),
                    "type": r_rel.type,
                    "properties": dict(r_rel)
                })
                
        return {"nodes": list(nodes.values()), "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Reconciliation APIs ---

# Temporary cached memory for MVP (ordinarily persisted to graph or document DB)
_reconciliation_cache = None

@router.get("/reconciliation/run")
def run_reconciliation():
    """
    Triggers the 3-way match logic and caches results.
    """
    global _reconciliation_cache
    try:
        summary, results = matcher.reconcile_all()
        _reconciliation_cache = {
            "summary": summary.model_dump(),
            "results": [r.model_dump() for r in results]
        }
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reconciliation/summary")
def get_reconciliation_summary():
    """
    Returns the top level summary stats. Runs it if not cached.
    """
    global _reconciliation_cache
    if not _reconciliation_cache:
        run_reconciliation()
    return _reconciliation_cache["summary"]

@router.get("/reconciliation/results")
def get_reconciliation_results(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Returns paginated array of mismatch details.
    """
    global _reconciliation_cache
    if not _reconciliation_cache:
        run_reconciliation()
        
    results = _reconciliation_cache["results"]
    
    # Filter
    if status:
        results = [r for r in results if r["match_status"] == status]
        
    # Paginate    
    start = (page - 1) * limit
    end = start + limit
    
    return {
        "page": page,
        "limit": limit,
        "total": len(results),
        "results": results[start:end]
    }

# --- Risk APIs ---

_risk_cache = None

@router.get("/risk/compute")
def compute_risk():
    """
    Executes ML and Rule scorers for all taxpayers in graph.
    """
    global _risk_cache, _reconciliation_cache
    
    if not _reconciliation_cache:
        run_reconciliation()
        
    try:
        # Get all GSTINs
        Q_GSTINS = "MATCH (t:Taxpayer) WHERE t._is_stub = false RETURN t.gstin AS gstin"
        gstins = []
        with db.get_session() as session:
            gstins = [r["gstin"] for r in session.run(Q_GSTINS)]
            
        circ = matcher._get_circular_trading_gstins()
        
        # We need the recon models back, since cache contains dicts
        # (For MVP simulation)
        from backend.schemas.reconciliation import ReconciliationResult
        recon_models = [ReconciliationResult(**r) for r in _reconciliation_cache["results"]]
            
        scores = composite_scorer.compute_all_vendor_scores(gstins, recon_models, circ)
        _risk_cache = {s.gstin: s.model_dump() for s in scores}
        
        return {"status": "success", "computed_count": len(scores)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk/scores")
def get_risk_scores(
    sort: str = "composite_score",
    order: str = "desc",
    limit: int = 50
):
    global _risk_cache
    if not _risk_cache:
        compute_risk()
        
    vendors = list(_risk_cache.values())
    
    # Sort
    rev = (order == "desc")
    vendors.sort(key=lambda x: x.get(sort, 0), reverse=rev)
    
    return {"vendors": vendors[:limit]}

@router.get("/risk/explain/{gstin}")
def get_risk_explanation(gstin: str):
    global _risk_cache
    if not _risk_cache:
        compute_risk()
        
    if gstin not in _risk_cache:
        raise HTTPException(status_code=404, detail="Vendor not found or no risk score.")
        
    return _risk_cache[gstin]

# --- Dashboard Unified ---

@router.get("/dashboard/overview")
def get_dashboard_overview():
    """
    Combines stats, reconciliation summary, and top risks into one call.
    """
    try:
        gstats = get_graph_stats()
        rsummary = get_reconciliation_summary()
        top_risks = get_risk_scores("composite_score", "desc", 5)
        
        return {
            "total_taxpayers": gstats["nodes"].get("Taxpayer", 0),
            "total_invoices": gstats["nodes"].get("Invoice", 0),
            "reconciliation": rsummary,
            "top_risk_vendors": top_risks["vendors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
