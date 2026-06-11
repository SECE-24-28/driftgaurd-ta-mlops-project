import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { getModels } from '../lib/api';
import { ShieldAlert } from 'lucide-react';

export default function Layout({ children, onRefresh, lastUpdated, isRefreshing, error }) {
  const [activeCount, setActiveCount] = useState(0);

  useEffect(() => {
    async function loadActiveCount() {
      try {
        const data = await getModels();
        if (Array.isArray(data)) {
          setActiveCount(data.length);
        }
      } catch (err) {
        console.error("Failed to load active model count in Layout:", err);
      }
    }
    loadActiveCount();
  }, [children]);

  return (
    <div className="flex bg-[#0d1117] min-h-screen text-[#e6edf3] font-sans antialiased overflow-hidden">
      {/* Sidebar */}
      <Sidebar activeModelCount={activeCount} />

      {/* Main content wrapper */}
      <div className="flex-1 flex flex-col h-screen overflow-y-auto">
        <TopBar onRefresh={onRefresh} lastUpdated={lastUpdated} isRefreshing={isRefreshing} />
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto relative">
          {/* Connection Error Banner */}
          {error ? (
            <div className="bg-[#3d1515] border border-[#5a1e1e] p-4 rounded-lg flex items-start space-x-3 text-xs text-[#f85149] animate-pulse-slow mb-6">
              <ShieldAlert className="w-5 h-5 flex-shrink-0" />
              <div className="space-y-0.5">
                <span className="font-bold">Connection Error:</span>
                <p className="text-[#7d8590]">{error}</p>
              </div>
            </div>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}
