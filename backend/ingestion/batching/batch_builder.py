"""
Batch assembly — produce the Contract-1 batch JSON envelope:

{
    "batch_metadata": {...},
    "entities": [{entity_type, ref_id, data}, ...],
    "rejected_records": [...]
}
"""

from datetime import datetime, timezone


def build_batch(entities: list[dict], rejected: list[dict], source_dir: str, contract_version: str = "1.0.0") -> dict:
    counts: dict[str, int] = {}
    for e in entities:
        counts[e["entity_type"]] = counts.get(e["entity_type"], 0) + 1

    return {
        "batch_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source_dir,
            "contract_version": contract_version,
            "entity_counts": counts,
            "accepted_total": len(entities),
            "rejected_total": len(rejected),
        },
        "entities": entities,
        "rejected_records": rejected,
    }
