import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { LayoutDashboard, Activity, Settings, LogOut } from 'lucide-react';
import { getMe } from '../lib/api';

export default function Sidebar({ activeModelCount }) {
  const router = useRouter();
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await getMe();
        setUser(data);
      } catch (err) {
        console.error("Failed to load user in sidebar:", err);
      }
    }
    loadUser();
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem("dg_api_key");
    router.replace("/login");
  };

  const navItems = [
    { label: 'Fleet Overview', icon: LayoutDashboard, path: '/dashboard' },
    { label: 'Model Metrics', icon: Activity, path: '/dashboard', badge: activeModelCount },
    { label: 'System Settings', icon: Settings, path: '/dashboard' }
  ];

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  };

  return (
    <div className="w-[240px] bg-[#161b22] border-r border-[#30363d] flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* Brand Header */}
        <div className="px-6 py-5 border-b border-[#30363d] flex items-center space-x-3">
          <span className="text-xl">🛡️</span>
          <div>
            <h1 className="text-sm font-extrabold tracking-wider text-[#e6edf3]">DRIFTGUARD</h1>
            <span className="text-[9px] text-[#7d8590] uppercase tracking-widest font-semibold">Self-Healing MLOps</span>
          </div>
        </div>

        {/* Navigation Section */}
        <nav className="mt-6 px-3 space-y-1">
          {navItems.map((item, idx) => {
            const Icon = item.icon;
            const isActive = router.pathname === item.path || (router.pathname.startsWith('/models/') && item.label === 'Model Metrics');
            return (
              <button
                key={idx}
                onClick={() => router.push(item.path)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all group ${
                  isActive
                    ? 'bg-[#1c2128] text-[#58a6ff] border border-[#30363d]'
                    : 'text-[#7d8590] hover:text-[#e6edf3] hover:bg-[#1c2128]/50 border border-transparent'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#58a6ff]' : 'text-[#7d8590] group-hover:text-[#e6edf3]'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 ? (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-[#1c2d3a] text-[#58a6ff] border border-[#243e56]/40 font-bold">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Footer Profile */}
      <div className="p-4 border-t border-[#30363d] bg-[#0d1117]/40 flex flex-col space-y-3">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#58a6ff] to-[#a371f7] flex items-center justify-center text-[11px] font-bold text-[#0d1117]">
            {user ? getInitials(user.name) : 'DG'}
          </div>
          <div className="flex-1 min-w-0">
            <span className="block text-xs font-semibold text-[#e6edf3] truncate">
              {user ? user.name : 'DriftGuard User'}
            </span>
            <span className="block text-[10px] text-[#7d8590] truncate">
              {user ? user.email : 'loading...'}
            </span>
          </div>
        </div>
        <button
          onClick={handleSignOut}
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg bg-[#21262d] border border-[#30363d] hover:bg-[#f85149] hover:text-[#e6edf3] hover:border-[#f85149] text-xs font-semibold text-[#7d8590] transition-all"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
