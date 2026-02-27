from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.api import router as api_router
from backend.graph.connection import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PramanaGST Knowledge Graph API",
    description="Backend API for GST Reconciliation and Risk AI",
    version="1.0.0"
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    try:
        db.verify_connectivity()
        logger.info("Successfully connected to Neo4j graph database.")
    except Exception as e:
        logger.warning(f"Failed to connect to Neo4j on startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    db.close()
    logger.info("Closed Neo4j connection pool.")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
