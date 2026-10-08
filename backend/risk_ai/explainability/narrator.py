"""
Explainability narrator — turns VendorRisk objects into auditor-readable text.

Deterministic template narration by default (auditable, offline, no key needed).
Set PRAMANAGST_LLM_URL + OPENAI_API_KEY to route through an LLM instead.
"""

import json
import os
from urllib import request as _urlrequest

from ..models.vendor_risk import VendorRisk

_SYSTEM_PROMPT = (
    "You are a GST audit assistant. Given a vendor risk JSON, write a concise "
    "(max 120 words) plain-English paragraph for a tax officer explaining the "
    "risk findings. Reference only facts present in the input."
)


def narrate(vendor: VendorRisk) -> str:
    if os.environ.get("PRAMANAGST_LLM_URL") and os.environ.get("OPENAI_API_KEY"):
        return _llm_narrative(vendor)
    return _template_narrative(vendor)


def _template_narrative(v: VendorRisk) -> str:
    s = v.signals
    lines = [
        f"Vendor {v.legal_name} ({v.gstin}) carries {v.band} compliance risk "
        f"(score {v.score}/100) based on {s.invoices_issued} issued invoice(s)."
    ]
    if not v.reasons:
        lines.append("No anomalies were detected across reconciliation, filing completeness, "
                     "tax payment, or trading-loop checks.")
    else:
        lines.append("Findings: " + "; ".join(v.reasons) + ".")
    try:
        from decimal import Decimal
        has_liability = Decimal(str(s.tax_liability or "0")) != 0
    except Exception:
        has_liability = s.tax_liability not in ("", "0", "0.00", "0.0")
    if has_liability:
        lines.append(f"Filed liability INR {s.tax_liability} against payments of INR {s.tax_paid}.")
    return " ".join(lines)


def _llm_narrative(v: VendorRisk) -> str:
    """OpenAI-compatible chat completion; falls back to template on any failure."""
    url = os.environ["PRAMANAGST_LLM_URL"].rstrip("/")
    body = json.dumps({
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": v.model_dump_json(by_alias=True)},
        ],
        "temperature": 0.2,
    }).encode()
    req = _urlrequest.Request(
        f"{url}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
    )
    import time as _time

    _start = _time.perf_counter()
    try:
        with _urlrequest.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as exc:
        # Template fallback keeps the audit flow alive; the failure is now
        # observable server-side (reason + latency only — never the payload).
        try:
            from backend.api.logging_setup import log_llm_fallback

            log_llm_fallback(type(exc).__name__, (_time.perf_counter() - _start) * 1000)
        except Exception:
            pass
        return _template_narrative(v)
