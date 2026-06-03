import React, { useState } from 'react';
import { ShieldCheck, Search, ChevronDown, ChevronUp } from 'lucide-react';

export default function AuditLog({ logs }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);

  if (!logs || logs.length === 0) {
    return (
      <div className="bg-obsidian-900 border border-slate-800 rounded-xl p-6 shadow-md text-center text-slate-500">
        No audit logs recorded.
      </div>
    );
  }

  const toggleExpand = (idx) => {
    if (expandedRow === idx) {
      setExpandedRow(null);
    } else {
      setExpandedRow(idx);
    }
  };

  // Filter logs based on search
  const filteredLogs = logs.filter((log) => {
    const term = searchTerm.toLowerCase();
    return (
      log.event_type.toLowerCase().includes(term) ||
      log.triggered_by.toLowerCase().includes(term) ||
      log.model_version.toLowerCase().includes(term) ||
      (log.details && JSON.stringify(log.details).toLowerCase().includes(term))
    );
  });

  const getEventBadge = (type) => {
    const base = "text-[10px] font-bold px-2 py-0.5 rounded uppercase border ";
    if (type === 'drift_detected') {
      return <span className={base + "bg-red-950/70 text-red-400 border-red-900 animate-pulse"}>Drift Detected</span>;
    } else if (type === 'retrain_triggered') {
      return <span className={base + "bg-blue-950/70 text-blue-400 border-blue-900"}>Retraining</span>;
    } else if (type === 'model_promoted') {
      return <span className={base + "bg-emerald-950/70 text-emerald-400 border-emerald-900"}>Model Promoted</span>;
    } else {
      return <span className={base + "bg-amber-950/70 text-amber-400 border-amber-900"}>Rollback</span>;
    }
  };

  return (
    <div className="bg-obsidian-900 border border-slate-800 rounded-xl p-6 shadow-md">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <h3 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-teal-500" />
          <span>Governance & Compliance Audit Trail</span>
        </h3>
        
        <div className="relative max-w-xs w-full">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search audit trail..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-teal-500 transition-colors"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/20">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900/60 text-slate-400 text-xs font-semibold uppercase">
            <tr>
              <th className="px-4 py-3">Timestamp (UTC)</th>
              <th className="px-4 py-3">Event Category</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Origin</th>
              <th className="px-4 py-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900 text-slate-300">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-4 py-8 text-center text-slate-500">
                  No records match your search criteria.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log, idx) => {
                const dateStr = new Date(log.timestamp).toLocaleString();
                const isExpanded = expandedRow === idx;
                
                return (
                  <React.Fragment key={idx}>
                    <tr
                      className="hover:bg-slate-900/20 transition-colors cursor-pointer"
                      onClick={() => toggleExpand(idx)}
                    >
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-450">{dateStr}</td>
                      <td className="px-4 py-3.5">{getEventBadge(log.event_type)}</td>
                      <td className="px-4 py-3.5 font-mono text-xs">{log.model_version}</td>
                      <td className="px-4 py-3.5 text-xs text-slate-400">{log.triggered_by}</td>
                      <td className="px-4 py-3.5 text-right">
                        <button className="text-teal-500 hover:text-teal-400 focus:outline-none inline-flex items-center space-x-1 text-xs">
                          <span>Inspect</span>
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-slate-950/70 border-t border-slate-900">
                        <td colSpan="5" className="px-4 py-4">
                          <div className="bg-slate-950 p-4 rounded-lg border border-slate-850">
                            <span className="text-[10px] text-slate-500 block uppercase font-bold mb-2">Audit Compliance Log Metadata (EU AI Act Payload)</span>
                            <pre className="text-xs text-slate-300 font-mono overflow-x-auto max-h-60 leading-relaxed">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
