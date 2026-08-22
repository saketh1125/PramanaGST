import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "./api";

const BAND_COLOR = { HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#22c55e" };
const LABEL_COLOR = {
  Taxpayer: "#60a5fa",
  Invoice: "#94a3b8",
  ReturnFiling: "#a78bfa",
  Payment: "#34d399",
  IRN: "#fbbf24",
};

function SummaryCard({ label, value, tone }) {
  return (
    <div className="card">
      <div className="card-value" style={tone ? { color: BAND_COLOR[tone] } : null}>
        {value}
      </div>
      <div className="card-label">{label}</div>
    </div>
  );
}

export default function App() {
  const [recon, setRecon] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [selected, setSelected] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [narrative, setNarrative] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.reconciliation(), api.risks()])
      .then(([r, v]) => { setRecon(r.summary); setVendors(v); })
      .catch((e) => setError(`API unreachable — start uvicorn. (${e.message})`));
  }, []);

  function selectVendor(gstin) {
    setSelected(gstin);
    setGraphData(null);
    setNarrative("…");
    api.explain(gstin).then((r) => setNarrative(r.narrative)).catch(() => setNarrative(""));
    api.egoGraph(gstin).then(setGraphData).catch(() => setGraphData({ nodes: [], links: [] }));
  }

  const graphProps = useMemo(() => ({
    nodeCanvasObject: (node, ctx, scale) => {
      const color = LABEL_COLOR[node.label] || "#64748b";
      const r = node.label === "Taxpayer" ? 7 : 4;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      if (scale > 1.5 || node.label === "Taxpayer") {
        ctx.font = `${4 / scale}px sans-serif`;
        ctx.fillStyle = "#cbd5e1";
        ctx.textAlign = "center";
        ctx.fillText(node.label === "Taxpayer" ? (node.legalName || node.id).slice(0, 18)
          : node.invoiceNumber || node.returnId?.slice(0, 16) || "", node.x, node.y - r - 2 / scale);
      }
    },
    linkColor: () => "#334155",
    linkDirectionalArrowLength: 3,
  }), []);

  return (
    <div className="shell">
      <header>
        <h1>Pramana<span>GST</span></h1>
        <p>Knowledge-graph GST reconciliation &amp; risk intelligence</p>
      </header>

      {error && <div className="error">{error}</div>}

      {recon && (
        <section className="cards">
          <SummaryCard label="Total claims" value={recon.totalClaims} />
          <SummaryCard label="Matched" value={recon.matched} tone="LOW" />
          <SummaryCard label="Mismatched" value={recon.mismatched} tone="MEDIUM" />
          <SummaryCard label="Unreported" value={recon.unreported} tone="HIGH" />
          <SummaryCard label="Match rate" value={`${recon.matchRate}%`} />
          <SummaryCard label="Tax at risk (INR)" value={Number(recon.varianceTotal).toLocaleString("en-IN")} tone="HIGH" />
        </section>
      )}

      <main className="split">
        <section className="panel">
          <h2>Vendor risk</h2>
          <table>
            <thead>
              <tr><th>Vendor</th><th>GSTIN</th><th>Invoices</th><th>Score</th><th>Band</th></tr>
            </thead>
            <tbody>
              {vendors.map((v) => (
                <tr key={v.gstin} onClick={() => selectVendor(v.gstin)}
                    className={v.gstin === selected ? "active" : ""}>
                  <td>{v.legalName}</td>
                  <td className="mono">{v.gstin}</td>
                  <td>{v.signals.invoicesIssued}</td>
                  <td>{v.score.toFixed(1)}</td>
                  <td><span className="badge" style={{ background: BAND_COLOR[v.band] }}>{v.band}</span></td>
                </tr>
              ))}
            </tbody>
          </table>

          {selected && narrative && (
            <div className="narrative">
              <h3>Audit note</h3>
              <p>{narrative}</p>
            </div>
          )}
        </section>

        <section className="panel graph-panel">
          <h2>{selected ? `Trading network — ${selected}` : "Select a vendor to inspect its network"}</h2>
          {graphData ? (
            <ForceGraph2D
              graphData={graphData}
              width={640}
              height={520}
              backgroundColor="#0b1120"
              {...graphProps}
            />
          ) : (
            <div className="placeholder">{selected ? "Loading…" : "No vendor selected"}</div>
          )}
          <div className="legend">
            {Object.entries(LABEL_COLOR).map(([label, color]) => (
              <span key={label}><i style={{ background: color }} />{label}</span>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
