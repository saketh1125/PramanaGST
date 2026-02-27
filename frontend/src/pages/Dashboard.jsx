import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { Activity, AlertTriangle, FileText, IndianRupee } from 'lucide-react';

const COLORS = {
    LOW: '#10B981',    // Green
    MEDIUM: '#F59E0B', // Yellow
    HIGH: '#EF4444',   // Red
    CRITICAL: '#7F1D1D'// Dark Red
};

export default function Dashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getDashboardOverview()
            .then(setData)
            .finally(() => setLoading(false));
    }, []);

    if (loading || !data) return <div className="p-8 text-center text-gray-500">Loading Dashboard...</div>;

    const riskData = Object.entries(data.reconciliation?.match_rate || {}).map(([key, val]) => ({
        name: key, value: val
    })); // Example - modify based on actual returned risk distribution

    const dummyRisk = [
        { name: 'Low Risk', value: 12 },
        { name: 'Medium Risk', value: 4 },
        { name: 'High Risk', value: 2 },
        { name: 'Critical', value: 2 },
    ];

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-gray-900">Command Center</h1>
                <div className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium border border-blue-200">
                    Last Updated: Just Now
                </div>
            </div>

            {/* Top Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard
                    title="Total Invoices"
                    value={data.total_invoices}
                    icon={<FileText className="text-blue-500" />}
                    subtitle="Processed"
                />
                <StatCard
                    title="Match Rate"
                    value={`${data.reconciliation.match_rate_percent}%`}
                    icon={<Activity className="text-green-500" />}
                    subtitle={`${data.reconciliation.full_match} Exact Matches`}
                />
                <StatCard
                    title="Tax At Risk"
                    value={`₹${(data.reconciliation.total_tax_at_risk / 100000).toFixed(2)}L`}
                    icon={<IndianRupee className="text-red-500" />}
                    subtitle="From mismatches"
                />
                <StatCard
                    title="High Risk Vendors"
                    value={(data.top_risk_vendors || []).filter(v => v.risk_level === 'CRITICAL' || v.risk_level === 'HIGH').length}
                    icon={<AlertTriangle className="text-orange-500" />}
                    subtitle="Require audit"
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Risk Distribution */}
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">Vendor Risk Distribution</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={dummyRisk}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    <Cell fill={COLORS.LOW} />
                                    <Cell fill={COLORS.MEDIUM} />
                                    <Cell fill={COLORS.HIGH} />
                                    <Cell fill={COLORS.CRITICAL} />
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top Risk Entities */}
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">CRITICAL Watchlist</h3>
                    <div className="space-y-4">
                        {(data.top_risk_vendors || []).slice(0, 5).map(vendor => (
                            <div key={vendor.gstin} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg transition-colors border border-transparent hover:border-gray-200">
                                <div>
                                    <div className="font-semibold text-gray-900">{vendor.legal_name}</div>
                                    <div className="text-xs text-gray-500 font-mono">{vendor.gstin}</div>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <div className="text-right">
                                        <div className="font-bold text-red-600">{vendor.composite_score || vendor.score} / 100</div>
                                    </div>
                                    <span className={`px-2.5 py-1 text-xs font-bold rounded-full text-white bg-red-700`}>
                                        {vendor.risk_level || vendor.level}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
}

function StatCard({ title, value, icon, subtitle }) {
    return (
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col justify-between">
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</h3>
                <div className="p-2 bg-gray-50 rounded-lg">{icon}</div>
            </div>
            <div>
                <div className="text-3xl font-bold text-gray-900">{value}</div>
                <div className="text-sm text-gray-500 mt-1">{subtitle}</div>
            </div>
        </div>
    );
}
