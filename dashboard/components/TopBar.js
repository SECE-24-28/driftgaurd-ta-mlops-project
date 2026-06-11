import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { RefreshCw, User } from 'lucide-react';
import { getMe } from '../lib/api';

export default function TopBar({ onRefresh, lastUpdated, isRefreshing }) {
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await getMe();
        setUser(data);
      } catch (err) {
        console.error("Failed to load user in top bar:", err);
      }
    }
    loadUser();
  }, []);

  const getPageTitle = () => {
    const { pathname, query } = router;
    if (pathname === '/dashboard') return 'Fleet Overview';
    if (pathname.startsWith('/models/')) return `Model Details > ${query.id || ''}`;
    return 'DriftGuard Console';
  };

  const formatLastUpdated = () => {
    if (!lastUpdated) return 'Never';
    const hours = String(lastUpdated.getHours()).padStart(2, '0');
    const minutes = String(lastUpdated.getMinutes()).padStart(2, '0');
    const seconds = String(lastUpdated.getSeconds()).padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  };

  return (
    <header className="h-[56px] border-b border-[#30363d] bg-[#161b22]/70 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Left: Breadcrumbs Page Title */}
      <div className="flex items-center space-x-2">
        <span className="text-xs text-[#7d8590] font-semibold tracking-wider uppercase">Console</span>
        <span className="text-xs text-[#7d8590] font-semibold">/</span>
        <h2 className="text-xs font-bold text-[#e6edf3] uppercase tracking-wider">{getPageTitle()}</h2>
      </div>

      {/* Right: Sync Status and User Profile */}
      <div className="flex items-center space-x-4">
        {onRefresh ? (
          <div className="flex items-center space-x-2">
            <span className="text-[10px] text-[#7d8590] font-mono">Last Sync: {formatLastUpdated()}</span>
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-1.5 rounded-lg border border-[#30363d] bg-[#21262d]/50 hover:bg-[#21262d] text-[#7d8590] hover:text-[#e6edf3] transition-all cursor-pointer active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        ) : null}
        <div className="h-4 w-[1px] bg-[#30363d]" />
        <div className="flex items-center space-x-2">
          <User className="w-3.5 h-3.5 text-[#7d8590]" />
          <span className="text-xs font-semibold text-[#e6edf3]">{user ? user.name : 'Loading User'}</span>
        </div>
      </div>
    </header>
  );
}
