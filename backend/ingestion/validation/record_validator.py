"""
Record validation — run each mapped entity through its Contract-1 model
and collect failures as structured rejected records.
"""

from typing import Any


def validate_entity(entity_type: str, ref_id: str, source: str, row_index: int, data: dict) -> dict:
    """Return an accepted entity record or a rejected-record dict."""
    from ..schemas import ENTITY_MODELS

    try:
        model = ENTITY_MODELS[entity_type]
        validated = model.model_validate(data)
        return {
            "entity_type": entity_type,
            "ref_id": ref_id,
            "data": validated.model_dump(by_alias=True, mode="json"),
        }
    except Exception as exc:
        errors = (
            [f"{e['loc']}: {e['msg']}" for e in exc.errors()] if hasattr(exc, "errors") else [str(exc)]
        )
        return {
            "rejected": True,
            "entity_type": entity_type,
            "ref_id": ref_id,
            "source_file": source,
            "row_index": row_index,
            "errors": errors,
        }


def summarize_rejections(rejected: list[dict[str, Any]]) -> dict:
    by_source: dict[str, int] = {}
    for r in rejected:
        by_source[r.get("source_file", "?")] = by_source.get(r.get("source_file", "?"), 0) + 1
    return {"total": len(rejected), "by_source": by_source}
