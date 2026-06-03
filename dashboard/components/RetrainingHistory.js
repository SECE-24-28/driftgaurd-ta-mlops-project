import React from 'react';
import { Calendar, CheckCircle2, XCircle, ArrowUpRight } from 'lucide-react';

export default function RetrainingHistory({ history }) {
  if (!history || history.length === 0) {
    return (
      <div className="bg-obsidian-900 border border-slate-800 rounded-xl p-6 shadow-md text-center text-slate-500">
        No retraining events logged for this model.
      </div>
    );
  }

  return (
    <div className="bg-obsidian-900 border border-slate-800 rounded-xl p-6 shadow-md">
      <h3 className="text-lg font-bold text-slate-100 mb-6 flex items-center space-x-2">
        <Calendar className="w-5 h-5 text-teal-500" />
        <span>Retraining & Calibration History</span>
      </h3>

      <div className="relative pl-6 border-l border-slate-800 space-y-8">
        {history.map((event, idx) => {
          const isSuccess = event.status === 'completed';
          const dateStr = new Date(event.start_time).toLocaleString();
          
          return (
            <div key={event.id || idx} className="relative">
              {/* Timeline marker */}
              <span className={`absolute -left-[31px] top-1 p-1.5 rounded-full border border-obsidian-900 ${
                isSuccess ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'
              }`}>
                {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              </span>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-500 font-medium">{dateStr}</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    isSuccess ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-900' : 'bg-red-950/70 text-red-400 border border-red-900'
                  }`}>
                    {event.status}
                  </span>
                </div>

                <div className="bg-slate-950/50 rounded-lg border border-slate-850 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-slate-200">
                      Version Bump: {event.old_version} → <span className="text-teal-400 font-bold">{event.new_version || 'Rejected'}</span>
                    </span>
                    {isSuccess && event.new_accuracy && (
                      <span className="flex items-center text-xs text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded">
                        <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
                        <span>+{((event.new_accuracy - event.old_accuracy)*100).toFixed(2)}%</span>
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs text-slate-400">
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase font-semibold">Champion Accuracy</span>
                      <span>{(event.old_accuracy * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-500 uppercase font-semibold">Challenger Accuracy</span>
                      <span>{event.new_accuracy ? `${(event.new_accuracy * 100).toFixed(2)}%` : 'N/A'}</span>
                    </div>
                  </div>

                  {event.details && event.details.message && (
                    <div className="mt-3 pt-2.5 border-t border-slate-850 text-xs text-slate-400 font-mono">
                      {event.details.message}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
