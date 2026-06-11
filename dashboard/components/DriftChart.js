import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer
} from 'recharts';
import { formatDriftScore } from '../lib/utils';

export default function DriftChart({ data, threshold }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-[#1c2128] border border-[#30363d] h-[350px] rounded-lg flex items-center justify-center text-[#7d8590] text-sm">
        No predictions recorded yet
      </div>
    );
  }

  const formatXAxis = (tickItem) => {
    if (!tickItem) return '';
    try {
      const d = new Date(tickItem);
      if (isNaN(d.getTime())) return tickItem;
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
    } catch (_) {
      return tickItem;
    }
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      const dateStr = new Date(item.timestamp).toLocaleString();
      return (
        <div className="drift-chart-tooltip">
          <p className="text-[10px] text-[#7d8590] font-semibold uppercase tracking-wider mb-1">Telemetry Record</p>
          <p className="font-semibold text-xs text-[#e6edf3] mb-1">Time: {dateStr}</p>
          <p className="font-semibold text-xs text-[#58a6ff]">Drift Score: {formatDriftScore(item.drift_score)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-[#1c2128] border border-[#30363d] p-5 rounded-lg shadow-md space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-[#e6edf3]">Drift Score — Last 100 Predictions</h3>
        <span className="text-[11px] font-semibold text-[#7d8590] bg-[#21262d] border border-[#30363d] px-2 py-0.5 rounded">
          Active Limit: {threshold}
        </span>
      </div>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#30363d" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              stroke="#7d8590"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: '#30363d' }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#7d8590"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: '#30363d' }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#30363d', strokeWidth: 1 }} />
            {threshold !== undefined && (
              <ReferenceLine
                y={threshold}
                stroke="#f85149"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                label={{
                  value: `Threshold (${threshold})`,
                  fill: '#f85149',
                  fontSize: 10,
                  position: 'top',
                  fontWeight: 'semibold'
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="drift_score"
              stroke="#58a6ff"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0, fill: '#58a6ff' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
