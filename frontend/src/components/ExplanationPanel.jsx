import React from 'react';
import { X, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export default function ExplanationPanel({ explanationData, isOpen, onClose }) {
    if (!isOpen || !explanationData) return null;

    const {
        legal_name,
        gstin,
        composite_score,
        risk_level,
        explanation,
        ml_explanation,
        triggered_rules
    } = explanationData;

    const getRiskColor = (lvl) => {
        switch (lvl) {
            case 'CRITICAL': return 'bg-red-700 text-white';
            case 'HIGH': return 'bg-red-500 text-white';
            case 'MEDIUM': return 'bg-orange-400 text-white';
            default: return 'bg-emerald-500 text-white';
        }
    }

    return (
        <div className="fixed inset-y-0 right-0 w-1/3 bg-white shadow-2xl border-l border-gray-200 z-50 transform transition-transform duration-300 overflow-y-auto">
            <div className="p-6">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">{legal_name}</h2>
                        <div className="text-sm font-mono text-gray-500 mt-1">{gstin}</div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex items-center space-x-4 mb-8">
                    <div className={`px-4 py-2 ${getRiskColor(risk_level)} rounded-lg font-bold tracking-widest`}>
                        {risk_level}
                    </div>
                    <div className="text-xl font-bold text-gray-700">
                        {composite_score} / 100
                    </div>
                </div>

                {/* Audit Trail */}
                <div className="mb-8 p-4 bg-gray-50 border-l-4 border-indigo-500 rounded-r-lg">
                    <h3 className="text-sm font-bold uppercase text-gray-500 mb-2">Audit Summary</h3>
                    <p className="text-gray-800 leading-relaxed text-sm">
                        {explanation}
                    </p>
                </div>

                {/* Triggered Rules */}
                {triggered_rules && triggered_rules.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-sm font-bold uppercase text-gray-500 mb-3 border-b pb-2">Rule Violations detected</h3>
                        <ul className="space-y-3">
                            {triggered_rules.map((rule, idx) => (
                                <li key={idx} className="flex items-start text-sm text-red-700 bg-red-50 p-3 rounded border border-red-100">
                                    <AlertCircle className="w-5 h-5 mr-3 shrink-0 text-red-500" />
                                    {rule}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* ML Explainability (SHAP proxy UI) */}
                {ml_explanation && ml_explanation.top_risk_factors && ml_explanation.top_risk_factors.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-sm font-bold uppercase text-gray-500 mb-3 border-b pb-2">AI Risk Drivers</h3>
                        <div className="space-y-4 pt-2">
                            {ml_explanation.top_risk_factors.map((factor, idx) => {
                                const isRisk = factor.direction === "increases risk";
                                return (
                                    <div key={idx} className="flex justify-between items-center bg-white border border-gray-100 p-3 rounded-lg shadow-sm">
                                        <div className="flex items-center space-x-3">
                                            {isRisk ? <TrendingUp className="text-red-500 w-4 h-4" /> : <TrendingDown className="text-green-500 w-4 h-4" />}
                                            <span className="text-sm font-medium text-gray-700 font-mono">
                                                {factor.feature.replace(/_/g, ' ')}
                                            </span>
                                        </div>
                                        <span className={`text-xs font-bold ${isRisk ? 'text-red-500' : 'text-green-500'}`}>
                                            Impact: {(factor.magnitude * 100).toFixed(1)}
                                        </span>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
