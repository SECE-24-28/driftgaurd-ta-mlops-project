import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { Activity, ShieldCheck, AlertCircle, RefreshCw, Layers } from 'lucide-react';
import ModelCard from '../components/ModelCard';

export default function Home() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      setModels(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const filteredModels = models.filter((m) =>
    m.model_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Compute aggregate statistics
  const totalModels = models.length;
  const unhealthyModels = models.filter((m) => m.status === 'degraded').length;
  const retrainingModels = models.filter((m) => m.status === 'retraining').length;
  const healthyModels = totalModels - unhealthyModels - retrainingModels;

  return (
    <div className="min-h-screen bg-obsidian-950 text-slate-150">
      <Head>
        <title>DriftGuard — Autonomous Model Health Platform</title>
        <meta name="description" content="Production-ready MLOps self-healing platform observability dashboard." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Main Navigation Bar */}
      <header className="border-b border-slate-900 bg-obsidian-900/60 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="p-2 bg-gradient-to-tr from-teal-500 to-indigo-600 rounded-lg shadow-inner">
              <Layers className="w-5 h-5 text-white" />
            </span>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-teal-400 to-cyan-200 bg-clip-text text-transparent">
                DRIFTGUARD
              </h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Autonomous MLOps Platform</p>
            </div>
          </div>
          <button
            onClick={fetchModels}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-900 text-xs text-slate-350 hover:text-slate-100 transition-all active:scale-95"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync Fleet</span>
          </button>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Observability Summary Stats Deck */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
          <div className="bg-obsidian-900 border border-slate-850 p-5 rounded-xl flex items-center justify-between shadow-lg">
            <div>
              <span className="text-xs text-slate-400 block font-semibold mb-1">Fleet Monitored</span>
              <span className="text-2xl font-black text-slate-100">{totalModels}</span>
            </div>
            <div className="p-3 bg-teal-950/50 text-teal-400 border border-teal-900/40 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-obsidian-900 border border-slate-850 p-5 rounded-xl flex items-center justify-between shadow-lg">
            <div>
              <span className="text-xs text-slate-400 block font-semibold mb-1">Stable Models</span>
              <span className="text-2xl font-black text-emerald-400">{healthyModels}</span>
            </div>
            <div className="p-3 bg-emerald-950/50 text-emerald-400 border border-emerald-900/40 rounded-lg">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-obsidian-900 border border-slate-850 p-5 rounded-xl flex items-center justify-between shadow-lg">
            <div>
              <span className="text-xs text-slate-400 block font-semibold mb-1">Active Retraining</span>
              <span className="text-2xl font-black text-cyan-400">{retrainingModels}</span>
            </div>
            <div className="p-3 bg-cyan-950/50 text-cyan-400 border border-cyan-900/40 rounded-lg">
              <RefreshCw className="w-5 h-5 animate-spin-slow" />
            </div>
          </div>

          <div className="bg-obsidian-900 border border-slate-850 p-5 rounded-xl flex items-center justify-between shadow-lg">
            <div>
              <span className="text-xs text-slate-400 block font-semibold mb-1">SLA Breaches</span>
              <span className="text-2xl font-black text-rose-500">{unhealthyModels}</span>
            </div>
            <div className="p-3 bg-red-950/50 text-red-400 border border-red-900/40 rounded-lg">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Filter and Search */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Model Observability Hub</h2>
            <p className="text-xs text-slate-400">Select a model deployment to inspect sliding-window Evidently reports, parameters, and audit logs.</p>
          </div>
          <input
            type="text"
            placeholder="Search model by ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 w-72 rounded-lg bg-obsidian-900 border border-slate-850 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
          />
        </div>

        {/* Models Grid */}
        {loading && models.length === 0 ? (
          <div className="h-64 flex items-center justify-center">
            <RefreshCw className="w-8 h-8 text-teal-500 animate-spin" />
          </div>
        ) : filteredModels.length === 0 ? (
          <div className="bg-obsidian-900 border border-slate-850 p-12 rounded-xl text-center text-slate-500 shadow-md">
            No monitored models located. Ensure DriftGuard wrap() telemetry triggers are firing.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {filteredModels.map((model) => (
              <ModelCard key={model.model_id} model={model} />
            ))}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        DriftGuard Platform © {new Date().getFullYear()} — Built for Production MLOps Health Observability.
      </footer>
    </div>
  );
}
