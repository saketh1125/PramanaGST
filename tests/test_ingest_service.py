"""Ingestion pipeline smoke test — Contract-1 batch assembly."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion.ingest_service import IngestService

DATA_DIR = os.path.join("backend", "ingestion", "dataset", "generated_data")


def _batch():
    return IngestService(DATA_DIR).process()


def test_batch_envelope():
    b = _batch()
    assert set(b) == {"batch_metadata", "entities", "rejected_records"}
    assert b["batch_metadata"]["accepted_total"] == len(b["entities"])
    assert b["batch_metadata"]["rejected_total"] == len(b["rejected_records"])


def test_expected_entity_counts():
    counts = _batch()["batch_metadata"]["entity_counts"]
    assert counts["TAXPAYER"] == 20
    assert counts["INVOICE"] == 100
    assert counts["SOURCE_OBSERVATION"] == 91
    assert counts["PAYMENT"] == 20
    assert counts["IRN"] == 90


def test_zero_rejections_on_valid_datasets():
    assert _batch()["rejected_records"] == []


def test_deterministic_ref_ids():
    e = {x["ref_id"] for x in _batch()["entities"]}
    assert e == {x["ref_id"] for x in _batch()["entities"]}
