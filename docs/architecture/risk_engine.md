# Deterministic Risk Engine, Evidence & Explanation Boundary

## 1. Deterministic risk engine

`backend/risk_ai/models/vendor_risk.py :: score_vendors(graph, recon_report)` is the
authoritative risk decision. It reads the knowledge graph plus Contract-3
reconciliation items and emits one `VendorRisk` per issuing taxpayer. No RNG, no
model weights to train, no network calls: identical inputs always produce identical
outputs (tests pin this in `tests/test_risk_engine_hardening.py`).

## 2. Risk factors

| Factor | Weight | Signal definition |
|---|---|---|
| ITC mismatch rate | 0.35 | mismatched claims / recon claims for the supplier |
| Ghost / unreported rate | 0.25 | supplied invoices with no `REPORTED_IN` edge / supplied invoices |
| Tax shortfall ratio | 0.25 | `max(liability − paid, 0)` / liability, clamped to ≤ 1 |
| Circular trading | 0.15 | membership in a strongly-connected taxpayer component |

`score = round(100 × Σ weight × signal, 2)`, clamped to [0, 100] by the model.
Liability comes from `Taxpayer —FILED→ GSTR-1 ReturnFiling` edges; payments from
`ReturnFiling —PAID_VIA→ Payment` edges. Money strings are canonical 2dp
(`"0.00"`, never `"0"`).

Bands: `HIGH ≥ 60`, `MEDIUM ≥ 30`, `LOW < 30`. Ties in score break on GSTIN so
vendor ordering is stable regardless of graph iteration order.

Known, tested limitations (see `tests/test_risk_engine_hardening.py`):
- Self-supply invoices (`supplier == recipient`) are excluded from the flow
  graph, so self-dealing never flags `in_cycle`.
- Ghost detection counts any `REPORTED_IN` edge to a `ReturnFiling:` node, while
  the matcher requires a GSTR-1 return — the same invoice can be `UNREPORTED` in
  reconciliation yet "reported" for ghost scoring.
- `mismatch_rate` uses recon claim counts; `invoicesIssued` uses graph invoice
  counts — denominators can legitimately differ.
- One payment linked from several GSTR-1 returns is summed once per return.
- A supplier missing from reconciliation silently scores zero mismatches.
- `recon_report` must carry `"items"` (KeyError otherwise) — strict by design.

## 3. Evidence generation

`_build_evidence()` runs inside the same scoring loop, so evidence can never
disagree with the score it explains. One `EvidenceItem` per finding:

- `MISMATCH` (reconciliation): `observed "m/n"`, `ratio`, `itemRefs` (claim refs,
  capped at 20), `path` (the item's `evidencePath`).
- `GHOST_UNREPORTED` (knowledge graph): unreported `Invoice:` node ids,
  `path = [Taxpayer, Invoice]`.
- `TAX_SHORTFALL` (knowledge graph): `liability`, `paid`, `shortfall`, involved
  GSTR-1 return and payment node ids.
- `CYCLE_MEMBERSHIP` (knowledge graph): `cycleSize`, sorted `memberGstins`,
  `Taxpayer:` node ids.

`VendorRisk.evidence` is an additive Contract-4 field (default `[]`); `reasons`
remain the human-readable projection of the same findings.

## 4. Investigation flow

Dashboard → select vendor → `GET /api/v1/risks/{gstin}` (score, band, signals,
evidence) → supporting-evidence panel renders each finding with its proof path →
`GET /api/v1/graph/ego/{gstin}` shows the surrounding network →
`GET /api/v1/risks/{gstin}/explain` produces the grounded audit note.
No new public contract was needed: investigation rides on Contract 4 detail
plus existing Contract 5 views.

## 5. LLM explanation boundary

`backend/risk_ai/explainability/narrator.py :: narrate(VendorRisk)`:

- The LLM receives the structured `VendorRisk` payload — including evidence —
  never raw graph state. Its system prompt restricts it to facts in the input.
- The LLM output is a string only. Score, band, signals, and evidence live on
  the `VendorRisk` object, which narration never mutates (tested).
- Any failure — missing env, unreachable endpoint, malformed output — falls
  back to the deterministic template narrator. The audit flow never depends on
  the LLM being available.

## 6. Why the LLM is NOT authoritative

An auditor must be able to reproduce a decision from inputs alone. The
deterministic engine satisfies this; an LLM call does not (model versions,
sampling, prompt drift). The architecture therefore keeps the LLM strictly
downstream of the decision: it explains established findings and must NOT
calculate risk, modify score/band, invent evidence, introduce unsupported risk
factors, or override deterministic findings.

## 7. Future decision-model research direction

"Evaluate privacy-preserving decision/reasoning models using de-identified
numerical and graph-derived features against the deterministic risk baseline."

That experiment is explicitly future scope: same de-identified feature vector,
compared against this deterministic baseline — never a silent replacement of it.
