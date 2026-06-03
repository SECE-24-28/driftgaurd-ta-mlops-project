import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine
} from 'recharts';

export default function DriftChart({ data }) {
  // Format dates for readability
  const formattedData = (data || []).map((item) => ({
    ...item,
    time: new Date(item.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    }),
    score: parseFloat(item.drift_score.toFixed(4))
  }));

  return (
    <div className="bg-obsidian-900 border border-slate-800 rounded-xl p-6 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-slate-100">Concept Drift History</h3>
          <p className="text-sm text-slate-400">Real-time rolling ADWIN values vs. evidently baseline</p>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <span className="inline-block w-3 h-3 bg-teal-500 rounded-full"></span>
          <span className="text-slate-400">Drift Score</span>
          <span className="inline-block w-3 h-1 border-t border-dashed border-red-500 ml-4"></span>
          <span className="text-slate-400">Limit (0.15)</span>
        </div>
      </div>

      <div className="h-72 w-full">
        {formattedData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500">
            Awaiting prediction telemetry streams...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <defs>
                <linearGradient id="driftGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0d9488" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '8px',
                  color: '#f1f5f9'
                }}
                labelStyle={{ color: '#94a3b8', fontSize: '12px' }}
              />
              <ReferenceLine y={0.15} stroke="#ef4444" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#0d9488"
                strokeWidth={2.5}
                dot={{ r: 2, fill: '#0d9488' }}
                activeDot={{ r: 5, fill: '#0d9488' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
