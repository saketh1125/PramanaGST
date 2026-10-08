"""Phase 1 — centralized configuration tests (no app import)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.config import load_settings


def test_dev_defaults_are_zero_config():
    s = load_settings({})
    assert s.env == "dev"
    assert s.docs_enabled is True
    assert s.api_key == ""
    assert "http://localhost:5173" in s.cors_origins
    assert s.data_dir.endswith(os.path.join("backend", "ingestion", "dataset", "generated_data"))
    assert s.neo4j_password == "pramanagst"  # dev-only convenience default


def test_prod_requires_api_key():
    with pytest.raises(RuntimeError, match="PRAMANAGST_API_KEY"):
        load_settings({"PRAMANAGST_ENV": "prod"})
    s = load_settings({"PRAMANAGST_ENV": "prod", "PRAMANAGST_API_KEY": "k"})
    assert s.docs_enabled is False
    assert s.cors_origins == ()


def test_prod_requires_neo4j_password_when_enabled():
    with pytest.raises(RuntimeError, match="NEO4J_PASSWORD"):
        load_settings({"PRAMANAGST_ENV": "prod", "PRAMANAGST_API_KEY": "k",
                       "PRAMANAGST_USE_NEO4J": "1"})
    s = load_settings({"PRAMANAGST_ENV": "prod", "PRAMANAGST_API_KEY": "k",
                       "PRAMANAGST_USE_NEO4J": "1", "NEO4J_PASSWORD": "s3cret"})
    assert s.neo4j_password == "s3cret"


def test_cors_origins_parsing():
    s = load_settings({"CORS_ORIGINS": "https://a.example, https://b.example ,, "})
    assert s.cors_origins == ("https://a.example", "https://b.example")


def test_data_dir_override():
    s = load_settings({"PRAMANAGST_DATA_DIR": "/tmp/demo"})
    assert s.data_dir == "/tmp/demo"


def test_port_workers_parsing():
    s = load_settings({"PORT": "9000", "WORKERS": "2"})
    assert (s.port, s.workers) == (9000, 2)
