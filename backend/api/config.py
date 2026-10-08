"""Centralized production configuration for the PramanaGST API.

All runtime configuration flows through here. Values come from the
environment (optionally via a local `.env` file loaded by the caller);
nothing secret is hardcoded. Development keeps zero-config defaults;
production fails fast when mandatory secrets are missing.
"""

import os
from dataclasses import dataclass


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_data_dir() -> str:
    return os.path.join(_repo_root(), "backend", "ingestion", "dataset", "generated_data")


def _csv_list(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass(frozen=True)
class Settings:
    env: str = "dev"
    data_dir: str = ""
    cors_origins: tuple = ()
    api_key: str = ""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    use_neo4j: bool = False
    llm_url: str = ""
    llm_api_key: str = ""
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    docs_enabled: bool = True


def _from_env(environ: dict = os.environ) -> Settings:
    env = environ.get("PRAMANAGST_ENV", "dev").lower()
    prod = env == "prod"
    return Settings(
        env=env,
        data_dir=environ.get("PRAMANAGST_DATA_DIR", _default_data_dir()),
        cors_origins=tuple(_csv_list(environ.get(
            "CORS_ORIGINS",
            "" if prod else "http://localhost:5173,http://127.0.0.1:5173",
        ))),
        api_key=environ.get("PRAMANAGST_API_KEY", ""),
        neo4j_uri=environ.get("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=environ.get("NEO4J_USER", "neo4j"),
        neo4j_password=environ.get("NEO4J_PASSWORD", "" if prod else "pramanagst"),
        use_neo4j=bool(environ.get("PRAMANAGST_USE_NEO4J", "")),
        llm_url=environ.get("PRAMANAGST_LLM_URL", "").rstrip("/"),
        llm_api_key=environ.get("OPENAI_API_KEY", ""),
        log_level=environ.get("PRAMANAGST_LOG_LEVEL", "INFO").upper(),
        host=environ.get("HOST", "127.0.0.1"),
        port=int(environ.get("PORT", "8000")),
        workers=int(environ.get("WORKERS", "1")),
        docs_enabled=not prod,
    )


def load_settings(environ: dict = os.environ) -> Settings:
    """Build settings and fail fast on unsafe production configuration."""
    settings = _from_env(environ)
    if settings.env == "prod":
        problems = []
        if not settings.api_key:
            problems.append("PRAMANAGST_API_KEY is required in prod")
        if settings.use_neo4j and not settings.neo4j_password:
            problems.append("NEO4J_PASSWORD is required in prod when PRAMANAGST_USE_NEO4J is set")
        if problems:
            raise RuntimeError("Invalid production configuration: " + "; ".join(problems))
    return settings


settings = load_settings()
