import React from 'react';
import { useRouter } from 'next/router';
import StatusBadge from './StatusBadge';
import { formatPercent, getAccuracyColor } from '../lib/utils';
import { Calendar, Eye, Layers } from 'lucide-react';

export default function ModelCard({ model }) {
  const router = useRouter();

  const handleDetails = () => {
    router.push(`/models/${model.model_id}`);
  };

  const accuracyVal = model.accuracy !== undefined && model.accuracy !== null ? model.accuracy : 0.0;
  const accuracyColorClass = getAccuracyColor(accuracyVal);
  const formattedAccuracy = model.accuracy !== undefined && model.accuracy !== null ? formatPercent(model.accuracy) : "—";

  // Parse features list
  let features = [];
  try {
    if (typeof model.features === 'string') {
      features = JSON.parse(model.features);
    } else if (Array.isArray(model.features)) {
      features = model.features;
    }
  } catch (e) {
    features = [];
  }

  const shownFeatures = features.slice(0, 3);
  const remainingCount = features.length - 3;

  return (
    <div className="bg-[#1c2128] border border-[#30363d] hover:border-[#58a6ff]/40 p-5 rounded-lg shadow-md hover:shadow-lg flex flex-col justify-between space-y-4 transition-all duration-300 group">
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2.5 min-w-0">
          <span className="p-1.5 bg-[#21262d] rounded text-[#58a6ff] border border-[#30363d]">
            <Layers className="w-3.5 h-3.5" />
          </span>
          <h3 className="text-sm font-bold text-[#e6edf3] truncate" title={model.model_id}>
            {model.model_id}
          </h3>
        </div>
        <StatusBadge status={model.status || 'healthy'} />
      </div>

      {/* Accuracy meter */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold text-[#7d8590]">
          <span>Champion Accuracy</span>
          <span className="text-[#e6edf3] font-mono">{formattedAccuracy}</span>
        </div>
        <div className="w-full bg-[#21262d] h-2 rounded-full overflow-hidden border border-[#30363d]/50">
          <div
            className={`h-full rounded-full transition-all duration-500 ${accuracyColorClass}`}
            style={{ width: `${Math.min(100, (accuracyVal > 1.0 ? accuracyVal : accuracyVal * 100))}%` }}
          />
        </div>
      </div>

      {/* Threshold & Features list */}
      <div className="space-y-2 pt-1 border-t border-[#30363d]/50">
        <div className="flex justify-between text-[11px] font-semibold text-[#7d8590]">
          <span>Drift Threshold:</span>
          <span className="text-[#58a6ff] font-mono font-bold">{model.drift_threshold !== null && model.drift_threshold !== undefined ? model.drift_threshold.toFixed(2) : 'N/A'}</span>
        </div>
        {features.length > 0 && (
          <div className="flex flex-wrap gap-1.5 items-center">
            {shownFeatures.map((feat, idx) => (
              <span key={idx} className="px-2 py-0.5 text-[9px] font-mono rounded bg-[#21262d] border border-[#30363d] text-[#7d8590]">
                {feat}
              </span>
            ))}
            {remainingCount > 0 && (
              <span className="text-[10px] text-[#7d8590] font-bold">
                +{remainingCount} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer Details action button */}
      <div className="flex items-center justify-between pt-2 border-t border-[#30363d]/50">
        <div className="flex items-center text-[10px] text-[#7d8590] space-x-1.5">
          <Calendar className="w-3.5 h-3.5" />
          <span>{model.version !== null && model.version !== undefined ? `v${model.version}` : 'N/A'}</span>
        </div>
        <button
          onClick={handleDetails}
          className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-[#21262d] border border-[#30363d] hover:bg-[#58a6ff] hover:text-[#0d1117] hover:border-[#58a6ff] text-xs font-bold text-[#e6edf3] transition-all cursor-pointer group-hover:border-[#58a6ff]/40 active:scale-95"
        >
          <Eye className="w-3.5 h-3.5" />
          <span>View Details</span>
        </button>
      </div>
    </div>
  );
}
