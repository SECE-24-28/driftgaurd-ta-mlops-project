"use client";

import { motion } from "framer-motion";
import { ArrowRight, Activity, DatabaseZap, ShieldCheck } from "lucide-react";

export function Hero() {
  return (
    <section className="pt-32 pb-20 md:pt-48 md:pb-32 px-4 relative overflow-hidden">
      <div className="container mx-auto grid lg:grid-cols-2 gap-12 items-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-block bg-accent text-background font-mono font-black px-4 py-2 border-2 border-foreground brutal-shadow-sm mb-6 uppercase tracking-wider">
            MLOps Platform 2.0
          </div>
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black uppercase leading-[1.1] tracking-tighter mb-6">
            Your AI Models Are <span className="text-primary glitch-text inline-block" data-text="Drifting">Drifting</span>.<br />
            We Stop Them.
          </h1>
          <p className="text-lg md:text-xl font-mono mb-8 max-w-lg bg-surface p-4 border-l-4 border-primary">
            Continuously monitor production models, detect data drift, trigger retraining pipelines, validate challenger models, and safely deploy updates without manual intervention.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 font-mono font-black uppercase tracking-wider">
            <button className="bg-primary text-background px-8 py-4 border-4 border-foreground brutal-button flex items-center justify-center gap-2 text-xl">
              Start Monitoring <ArrowRight className="w-6 h-6" strokeWidth={3} />
            </button>
            <button className="bg-background text-foreground px-8 py-4 border-4 border-foreground brutal-button flex items-center justify-center gap-2 text-xl hover:bg-surface">
              Watch Demo
            </button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="relative mt-12 lg:mt-0"
        >
          {/* Brutalist Dashboard Mockup */}
          <div className="bg-surface border-4 border-foreground brutal-shadow p-6 relative z-10 w-full max-w-md mx-auto lg:max-w-none">
            <div className="flex items-center justify-between border-b-4 border-foreground pb-4 mb-6">
              <div className="font-mono font-black text-xl uppercase tracking-wider">Live Telemetry</div>
              <div className="flex gap-2">
                <div className="w-4 h-4 bg-primary border-2 border-foreground"></div>
                <div className="w-4 h-4 bg-accent border-2 border-foreground"></div>
                <div className="w-4 h-4 bg-secondary border-2 border-foreground"></div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-background border-4 border-foreground p-4 brutal-shadow-sm hover:-translate-y-1 transition-transform">
                <div className="flex items-center gap-2 font-mono font-bold uppercase mb-2">
                  <Activity className="w-5 h-5 text-primary" strokeWidth={3} /> Drift Score
                </div>
                <div className="text-4xl font-black text-primary glitch-text" data-text="0.84">0.84 <span className="text-sm text-foreground block mt-1">WARNING</span></div>
              </div>
              <div className="bg-background border-4 border-foreground p-4 brutal-shadow-sm hover:-translate-y-1 transition-transform">
                <div className="flex items-center gap-2 font-mono font-bold uppercase mb-2">
                  <DatabaseZap className="w-5 h-5 text-accent" strokeWidth={3} /> Retraining
                </div>
                <div className="text-4xl font-black text-accent glitch-text" data-text="3">3 <span className="text-sm text-foreground block mt-1">ACTIVE JOBS</span></div>
              </div>
            </div>

            <div className="bg-background border-4 border-foreground p-4 brutal-shadow-sm h-48 relative overflow-hidden flex items-end justify-between px-2 gap-2">
               {/* Mock Chart Bars */}
               {[40, 70, 45, 90, 65, 80, 50, 85].map((h, i) => (
                 <div key={i} className="flex-1 bg-primary border-t-4 border-l-4 border-r-4 border-foreground hover:bg-accent transition-colors" style={{ height: `${h}%` }}></div>
               ))}
               <div className="absolute top-4 left-4 font-mono font-black text-sm bg-foreground text-background px-3 py-1 uppercase tracking-widest border-2 border-background">ACCURACY TREND</div>
            </div>
            
            <div className="mt-6 flex items-start gap-3 bg-secondary/20 text-foreground font-mono font-bold p-4 border-4 border-secondary brutal-shadow-sm">
              <ShieldCheck className="w-6 h-6 text-secondary shrink-0 mt-1" strokeWidth={3} />
              <div>
                <div className="text-secondary uppercase mb-1">System Update</div>
                Challenger model validation successful. Deployed v2.4.1.
              </div>
            </div>
          </div>
          
          {/* Decorative blocks */}
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-accent border-4 border-foreground z-0 brutal-shadow hidden md:block"></div>
          <div className="absolute -bottom-10 -left-10 w-24 h-24 bg-primary border-4 border-foreground z-0 brutal-shadow-sm hidden md:block" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)'}}></div>
        </motion.div>
      </div>
    </section>
  );
}
