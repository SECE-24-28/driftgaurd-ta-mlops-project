import React, { useState } from 'react';
import { formatDate, formatPercent } from '../lib/utils';
import StatusBadge from './StatusBadge';
import { ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';

export default function RetrainingHistory({ events }) {
  const [showAll, setShowAll] = useState(false);

  if (!events || events.length === 0) {
    return (
      <div className="bg-[#1c2128] border border-[#30363d] p-5 rounded-lg text-center text-[#7d8590] text-sm">
        No retraining events recorded yet
      </div>
    );
  }

  const sortedEvents = [...events].sort((a, b) => new Date(b.start_time) - new Date(a.start_time));
  const displayedEvents = showAll ? sortedEvents : sortedEvents.slice(0, 10);
  const hasMore = sortedEvents.length > 10;

  const getDotColor = (status) => {
    switch (String(status).toLowerCase()) {
      case 'completed':
        return 'bg-[#3fb950] ring-[#1a4731]';
      case 'running':
        return 'bg-[#58a6ff] ring-[#1c2d3a] animate-pulse';
      case 'failed':
        return 'bg-[#f85149] ring-[#3d1515]';
      default:
        return 'bg-[#7d8590] ring-[#21262d]';
    }
  };

  const renderAccuracyChange = (event) => {
    if (
      event.status !== 'completed' ||
      event.old_accuracy === null ||
      event.old_accuracy === undefined ||
      event.new_accuracy === null ||
      event.new_accuracy === undefined
    ) {
      return null;
    }
    const oldAcc = event.old_accuracy;
    const newAcc = event.new_accuracy;
    const diff = newAcc - oldAcc;
    const percentChange = (diff * 100).toFixed(1);
    const isImproved = diff > 0;
    const isNeutral = diff === 0;

    return (
      <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-[#e6edf3] bg-[#0d1117] px-2 py-1 rounded border border-[#30363d] mt-2 w-fit">
        <span>{event.old_version !== null && event.old_version !== undefined ? `v${event.old_version}` : 'N/A'}</span>
        <ArrowRight className="w-3 h-3 text-[#7d8590]" />
        <span>{event.new_version !== null && event.new_version !== undefined ? `v${event.new_version}` : 'N/A'}</span>
        <span className="text-[#7d8590]">|</span>
        <span>Acc: {formatPercent(oldAcc)}</span>
        <ArrowRight className="w-3 h-3 text-[#7d8590]" />
        <span>{formatPercent(newAcc)}</span>
        <span className={`font-bold ${isImproved ? 'text-[#3fb950]' : isNeutral ? 'text-[#7d8590]' : 'text-[#f85149]'}`}>
          {isImproved ? `+${percentChange}%` : `${percentChange}%`}
        </span>
      </div>
    );
  };

  return (
    <div className="bg-[#1c2128] border border-[#30363d] p-5 rounded-lg shadow-md flex flex-col space-y-4">
      <h3 className="text-sm font-bold text-[#e6edf3]">Retraining Events Timeline</h3>

      {/* Vertical Timeline */}
      <div className="relative pl-6 border-l border-[#30363d] space-y-6">
        {displayedEvents.map((ev, idx) => (
          <div key={ev.id || idx} className="relative group">
            {/* Circle Dot marker */}
            <span className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full ring-4 ${getDotColor(ev.status)}`} />

            {/* Event Content */}
            <div className="space-y-1">
              <div className="flex items-center space-x-2.5">
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                  ev.triggered_by === 'manual'
                    ? 'bg-[#1c2d3a] text-[#58a6ff] border border-[#243e56]/40'
                    : 'bg-[#21262d] text-[#e6edf3] border border-[#30363d]'
                }`}>
                  {ev.triggered_by || 'auto'}
                </span>
                <span className="text-[10px] text-[#7d8590] font-mono">
                  {formatDate(ev.start_time)}
                </span>
                <span className="ml-auto">
                  <StatusBadge status={ev.status} />
                </span>
              </div>
              <p className="text-xs text-[#e6edf3] font-medium leading-relaxed">
                {ev.status === 'completed'
                  ? 'Retraining pipeline completed successfully.'
                  : ev.status === 'running'
                  ? 'Retraining flow is currently executing steps...'
                  : ev.details?.message || ev.error || 'Retraining event failed during execution.'}
              </p>
              {renderAccuracyChange(ev)}
            </div>
          </div>
        ))}
      </div>

      {/* View all toggle */}
      {hasMore && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full flex items-center justify-center space-x-1.5 py-2 rounded-lg bg-[#21262d] border border-[#30363d] hover:bg-[#30363d] text-xs font-semibold text-[#58a6ff] transition-all cursor-pointer mt-4"
        >
          {showAll ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              <span>Show Less</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              <span>View All ({events.length} events)</span>
            </>
          )}
        </button>
      )}
    </div>
  );
}
