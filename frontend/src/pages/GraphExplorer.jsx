import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import GraphCanvas from '../components/GraphCanvas';
import { Search } from 'lucide-react';

export default function GraphExplorer() {
    const [gstin, setGstin] = useState('29AABCA0001A1Z5');
    const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        api.getGraphStats().then(setStats);
        handleSearch(); // load initial graph
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleSearch = () => {
        if (!gstin) return;
        setLoading(true);
        api.getVendorSubgraph(gstin)
            .then(res => {
                // Transform Neo4j flat format to Cytoscape elements array
                const elements = [
                    ...res.nodes.map(n => ({ data: { ...n.properties, id: n.id, _label: n.label } })),
                    ...res.edges.map(e => ({ data: { ...e.properties, id: e.id, source: e.source, target: e.target, _type: e.type } }))
                ];
                setGraphData(elements);
            })
            .catch(err => alert("Graph error: " + err.message))
            .finally(() => setLoading(false));
    };

    return (
        <div className="h-[calc(100vh-4rem)] flex flex-col p-6 space-y-4">
            <div className="flex justify-between items-end bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                <div className="w-1/3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Explore Subgraph</label>
                    <div className="relative flex items-center">
                        <Search className="w-5 h-5 absolute left-3 text-gray-400" />
                        <input
                            type="text"
                            value={gstin}
                            onChange={e => setGstin(e.target.value)}
                            className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-l-lg focus:ring-blue-500 focus:border-blue-500 font-mono"
                            placeholder="Enter GSTIN (e.g., 29XYZ...)"
                        />
                        <button
                            onClick={handleSearch}
                            className="bg-blue-600 text-white px-4 py-2 rounded-r-lg font-medium hover:bg-blue-700 transition"
                        >
                            Analyze
                        </button>
                    </div>
                </div>

                {stats && (
                    <div className="flex space-x-6 text-sm text-gray-600">
                        <div><span className="font-bold text-gray-900">{stats.nodes?.Taxpayer || 0}</span> Taxpayers</div>
                        <div><span className="font-bold text-gray-900">{stats.nodes?.Invoice || 0}</span> Invoices</div>
                        <div><span className="font-bold text-gray-900">{stats.relationships?.REPORTED_IN || 0}</span> Return Links</div>
                    </div>
                )}
            </div>

            <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden relative">
                {loading && (
                    <div className="absolute inset-0 bg-white/70 z-10 flex items-center justify-center font-semibold text-gray-600">
                        Traversing Graph...
                    </div>
                )}
                <div className="absolute top-4 right-4 z-10 bg-white/90 p-3 rounded shadow text-xs space-y-2 border">
                    <div className="font-bold uppercase tracking-wider text-gray-500 mb-2">Legend</div>
                    <div className="flex items-center"><span className="w-3 h-3 rounded bg-blue-500 mr-2"></span> Taxpayer</div>
                    <div className="flex items-center"><span className="w-3 h-3 rounded-full bg-indigo-500 mr-2"></span> Invoice</div>
                    <div className="flex items-center"><span className="w-3 h-3 rounded-sm bg-purple-500 mr-2"></span> Return / Observation</div>
                </div>

                {graphData.length > 0 ? (
                    <GraphCanvas elements={graphData} />
                ) : (
                    <div className="h-full flex items-center justify-center text-gray-400">Search a GSTIN to visualize topology</div>
                )}
            </div>
        </div>
    );
}
