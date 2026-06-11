"use client";

import { motion } from "framer-motion";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const driftData = [
  { time: '00:00', score: 0.1, threshold: 0.5 },
  { time: '04:00', score: 0.2, threshold: 0.5 },
  { time: '08:00', score: 0.3, threshold: 0.5 },
  { time: '12:00', score: 0.6, threshold: 0.5 },
  { time: '16:00', score: 0.8, threshold: 0.5 },
  { time: '20:00', score: 0.15, threshold: 0.5 },
];

const accuracyData = [
  { version: 'v1.0', accuracy: 0.92 },
  { version: 'v1.1', accuracy: 0.94 },
  { version: 'v1.2', accuracy: 0.91 },
  { version: 'v2.0', accuracy: 0.96 },
];

export function DashboardPreview() {
  return (
    <section className="py-16 px-4 bg-background border-b-4 border-foreground overflow-hidden">
      <div className="container mx-auto">
        <div className="flex flex-col md:flex-row items-end justify-between mb-6 border-b-8 border-foreground pb-8 gap-4">
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter max-w-2xl">
            Production-Grade <br/> <span className="text-accent glitch-text inline-block" data-text="Monitoring">Monitoring</span> Dashboard
          </h2>
          <div className="font-sans font-black text-xl uppercase bg-primary text-foreground px-4 py-2 border-4 border-foreground brutal-shadow">
            FULL VISIBILITY
          </div>
        </div>

        <div className="border-4 border-foreground bg-surface brutal-shadow p-2 md:p-5">
          {/* Dashboard Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b-4 border-foreground pb-4 mb-6 px-2 gap-4">
             <div className="flex items-center gap-4">
                <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-foreground animate-pulse"></div>
                <span className="font-sans font-black text-xl uppercase">Live Production System</span>
             </div>
             <div className="font-sans font-bold px-3 py-1 bg-background border-2 border-foreground uppercase text-sm">
                Last updated: Just now
             </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-5">
            {/* Drift Chart */}
            <div className="lg:col-span-2 border-4 border-foreground bg-background p-4 brutal-shadow-sm hover:bg-surface transition-colors">
              <h3 className="font-sans font-black uppercase mb-4 border-b-2 border-foreground pb-2">Data Drift Score over Time</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={driftData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="time" stroke="#F9FAFB" tick={{fontFamily: 'monospace'}} />
                    <YAxis stroke="#F9FAFB" tick={{fontFamily: 'monospace'}} />
                    <Tooltip contentStyle={{backgroundColor: '#111827', border: '2px solid #F9FAFB', borderRadius: 0, fontFamily: 'monospace'}} />
                    <Area type="step" dataKey="threshold" stroke="#ef4444" fill="transparent" strokeWidth={2} strokeDasharray="5 5" />
                    <Area type="monotone" dataKey="score" stroke="#6366F1" fill="#6366F1" fillOpacity={0.3} strokeWidth={4} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Model Accuracy */}
            <div className="border-4 border-foreground bg-background p-4 brutal-shadow-sm hover:bg-surface transition-colors">
              <h3 className="font-sans font-black uppercase mb-4 border-b-2 border-foreground pb-2">Model Accuracy</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={accuracyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="version" stroke="#F9FAFB" tick={{fontFamily: 'monospace'}} />
                    <YAxis domain={[0.8, 1]} stroke="#F9FAFB" tick={{fontFamily: 'monospace'}} />
                    <Tooltip cursor={{fill: '#111827'}} contentStyle={{backgroundColor: '#111827', border: '2px solid #F9FAFB', borderRadius: 0, fontFamily: 'monospace'}} />
                    <Bar dataKey="accuracy" fill="#06B6D4" stroke="#F9FAFB" strokeWidth={2} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent Events Log */}
            <div className="lg:col-span-3 border-4 border-foreground bg-background p-4 brutal-shadow-sm mt-4">
              <h3 className="font-sans font-black uppercase mb-4 border-b-2 border-foreground pb-2">Audit & Action Log</h3>
              <div className="font-sans space-y-3 overflow-x-auto">
                 <div className="flex items-center gap-4 text-sm md:text-base border-l-4 border-primary pl-4 py-1 min-w-[500px]">
                    <span className="text-muted-foreground w-24 shrink-0">12:05 PM</span>
                    <span className="bg-primary text-foreground px-2 font-bold shrink-0">INFO</span>
                    <span className="truncate">Promoted Challenger Model v2.0 to Champion.</span>
                 </div>
                 <div className="flex items-center gap-4 text-sm md:text-base border-l-4 border-green-500 pl-4 py-1 min-w-[500px]">
                    <span className="text-muted-foreground w-24 shrink-0">11:45 AM</span>
                    <span className="bg-green-500 text-foreground px-2 font-bold shrink-0">SUCCESS</span>
                    <span className="truncate">Challenger validation passed. Accuracy +4%.</span>
                 </div>
                 <div className="flex items-center gap-4 text-sm md:text-base border-l-4 border-accent pl-4 py-1 min-w-[500px]">
                    <span className="text-muted-foreground w-24 shrink-0">08:15 AM</span>
                    <span className="bg-accent text-foreground px-2 font-bold shrink-0">JOB</span>
                    <span className="truncate">Automated retraining job completed.</span>
                 </div>
                 <div className="flex items-center gap-4 text-sm md:text-base border-l-4 border-red-500 pl-4 py-1 min-w-[500px]">
                    <span className="text-muted-foreground w-24 shrink-0">07:50 AM</span>
                    <span className="bg-red-500 text-foreground px-2 font-bold shrink-0">ALERT</span>
                    <span className="truncate">Drift score 0.6 exceeded threshold 0.5.</span>
                 </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
