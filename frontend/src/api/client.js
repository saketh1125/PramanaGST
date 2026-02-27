import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Dashboard
  getDashboardOverview: () => apiClient.get('/dashboard/overview').then(res => res.data),
  
  // Reconciliation
  getReconciliationSummary: () => apiClient.get('/reconciliation/summary').then(res => res.data),
  getReconciliationResults: (params) => apiClient.get('/reconciliation/results', { params }).then(res => res.data),
  
  // Risk
  getRiskScores: (params) => apiClient.get('/risk/scores', { params }).then(res => res.data),
  getRiskExplanation: (gstin) => apiClient.get(`/risk/explain/${gstin}`).then(res => res.data),
  
  // Graph
  getGraphStats: () => apiClient.get('/graph/stats').then(res => res.data),
  getVendorSubgraph: (gstin) => apiClient.get(`/graph/subgraph/${gstin}`).then(res => res.data),
};
