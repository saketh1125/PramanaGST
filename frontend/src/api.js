const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

export const api = {
  reconciliation: () => get("/api/v1/reconciliation"),
  risks: () => get("/api/v1/risks"),
  explain: (gstin) => get(`/api/v1/risks/${gstin}/explain`),
  egoGraph: (gstin, depth = 2) => get(`/api/v1/graph/ego/${gstin}?depth=${depth}`),
};
