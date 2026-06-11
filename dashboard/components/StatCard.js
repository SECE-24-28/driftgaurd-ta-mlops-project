import React from 'react';

export default function StatCard({ label, value, color }) {
  const colorMap = {
    blue: 'text-[#58a6ff]',
    green: 'text-[#3fb950]',
    amber: 'text-[#d29922]',
    red: 'text-[#f85149]',
    purple: 'text-[#a371f7]',
    text: 'text-[#e6edf3]',
    muted: 'text-[#7d8590]'
  };

  const textClass = colorMap[color] || color || 'text-[#e6edf3]';

  return (
    <div className="bg-[#1c2128] border border-[#30363d] p-5 rounded-lg shadow-md hover:border-[#58a6ff]/30 transition-all duration-300">
      <span className="text-xs text-[#7d8590] uppercase tracking-wider font-semibold block mb-1">
        {label}
      </span>
      <span className={`text-2xl font-black tracking-tight ${textClass}`}>
        {value}
      </span>
    </div>
  );
}
