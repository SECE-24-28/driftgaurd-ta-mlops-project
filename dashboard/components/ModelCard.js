import React from 'react';
import Link from 'next/link';
import { Activity, ShieldAlert, CheckCircle, RefreshCw } from 'lucide-react';

export default function ModelCard({ model }) {
  const { model_id, status, accuracy, version, features } = model;

  // Compute status styles
  let statusBadge = null;
  if (status === 'healthy') {
    statusBadge = (
      <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
        <CheckCircle className="w-3.5 h-3.5" />
        <span>Healthy</span>
      </span>
    );
  } else if (status === 'degraded') {
    statusBadge = (
      <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-950 text-red-400 border border-red-800 animate-pulse">
        <ShieldAlert className="w-3.5 h-3.5" />
        <span>Degraded</span>
      </span>
    );
  } else {
    statusBadge = (
      <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800 animate-spin-slow">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        <span>Retraining</span>
      </span>
    );
  }

  return (
    <div className="bg-obsidian-900 border border-slate-800 hover:border-teal-500/50 transition-all duration-300 rounded-xl p-6 shadow-md hover:shadow-teal-500/5 cursor-pointer flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-slate-800/50 rounded-lg text-teal-500">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-md font-bold text-slate-100">{model_id}</h4>
              <p className="text-xs text-slate-400">Ver: {version}</p>
            </div>
          </div>
          {statusBadge}
        </div>

        <div className="grid grid-cols-2 gap-4 my-6">
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-850">
            <span className="text-[10px] text-slate-500 block uppercase font-semibold">Base Accuracy</span>
            <span className="text-lg font-bold text-slate-200">{(accuracy * 100).toFixed(2)}%</span>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-850">
            <span className="text-[10px] text-slate-500 block uppercase font-semibold">Features Tracked</span>
            <span className="text-lg font-bold text-slate-200">{features ? features.length : 0}</span>
          </div>
        </div>
      </div>

      <Link href={`/models/${model_id}`} className="mt-4 block text-center py-2 px-4 rounded-lg bg-teal-600 hover:bg-teal-500 font-medium text-sm text-slate-100 transition-colors duration-200">
        Open Health Monitor
      </Link>
    </div>
  );
}
