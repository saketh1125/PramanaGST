import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShieldAlert, GitGraph, FileSearch, HelpCircle } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Reconciliation from './pages/Reconciliation';
import GraphExplorer from './pages/GraphExplorer';
// We didn't build a separate full risk page in this phase, so we'll route to dashboard or a placeholder
// In the MVP the risk components pop up via ExplanationPanel in Dashboard/Graph.

function AppLayout({ children }) {
    const location = useLocation();
    const isActive = (path) => location.pathname === path ? 'bg-blue-800 text-white' : 'text-blue-100 hover:bg-blue-800';

    return (
        <div className="flex h-screen bg-gray-50 overflow-hidden font-sans">

            {/* Sidebar */}
            <div className="w-64 bg-slate-900 text-white flex flex-col shadow-xl z-20">
                <div className="h-16 flex items-center px-6 font-bold text-2xl tracking-tight border-b border-slate-800">
                    <span className="text-blue-500 mr-2">⬡</span> Pramana<span className="text-gray-400 font-light">GST</span>
                </div>

                <nav className="flex-1 px-4 py-6 space-y-2">
                    <Link to="/" className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${isActive('/')}`}>
                        <LayoutDashboard className="w-5 h-5" />
                        <span className="font-medium">Dashboard</span>
                    </Link>
                    <Link to="/reconciliation" className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${isActive('/reconciliation')}`}>
                        <FileSearch className="w-5 h-5" />
                        <span className="font-medium">Reconciliation</span>
                    </Link>
                    <Link to="/graph" className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${isActive('/graph')}`}>
                        <GitGraph className="w-5 h-5" />
                        <span className="font-medium">Graph Explorer</span>
                    </Link>
                    <div className="mt-8 pt-6 border-t border-slate-800">
                        <div className="text-xs uppercase text-slate-500 font-bold tracking-widest px-4 mb-2">Modules</div>
                        <div className="flex items-center space-x-3 px-4 py-2 text-slate-400 opacity-50 cursor-not-allowed">
                            <ShieldAlert className="w-5 h-5" />
                            <span className="font-medium">Risk Profiles</span>
                        </div>
                    </div>
                </nav>

                {/* User profile mocked */}
                <div className="p-4 border-t border-slate-800 flex items-center space-x-3 bg-slate-950/30">
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold">A</div>
                    <div>
                        <div className="text-sm font-medium">Auditor Admin</div>
                        <div className="text-xs text-slate-400">Pramana Network</div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 z-10">
                    <div className="text-sm text-gray-500">Node Location: <span className="font-mono text-gray-800 ml-1">ap-south-1</span></div>
                    <div className="flex items-center space-x-4 text-gray-500">
                        <HelpCircle className="w-5 h-5 hover:text-gray-800 cursor-pointer" />
                    </div>
                </header>
                <main className="flex-1 overflow-y-auto">
                    {children}
                </main>
            </div>

        </div>
    )
}

function App() {
    return (
        <BrowserRouter>
            <AppLayout>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/reconciliation" element={<Reconciliation />} />
                    <Route path="/graph" element={<GraphExplorer />} />
                </Routes>
            </AppLayout>
        </BrowserRouter>
    );
}

export default App;
