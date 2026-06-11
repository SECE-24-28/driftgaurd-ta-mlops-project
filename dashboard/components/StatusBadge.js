import React from 'react';
import { getStatusColor } from '../lib/utils';

export default function StatusBadge({ status }) {
  const colorClass = getStatusColor(status);
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${colorClass}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5"></span>
      {status}
    </span>
  );
}
