"use client";

import { motion } from "framer-motion";
import { Server, Cpu, Database, Network, GitBranch, Shield, LayoutDashboard } from "lucide-react";

export function Architecture() {
  const components = [
    { id: "sdk", name: "SDK / API", icon: Network, color: "text-primary" },
    { id: "engine", name: "Drift Engine", icon: Cpu, color: "text-accent" },
    { id: "pipeline", name: "Retraining", icon: GitBranch, color: "text-secondary" },
    { id: "validation", name: "Validation", icon: Shield, color: "text-green-500" },
    { id: "mlflow", name: "MLflow", icon: Database, color: "text-blue-500" },
    { id: "dashboard", name: "Dashboard", icon: LayoutDashboard, color: "text-amber-500" },
  ];

  return (
    <section id="architecture" className="py-16 px-4 bg-surface border-b-4 border-foreground">
      <div className="container mx-auto">
        <div className="text-center mb-6">
          <div className="inline-block bg-primary text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg">
            Under the Hood
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            System Architecture
          </h2>
        </div>

        <div className="max-w-4xl mx-auto border-4 border-foreground bg-background p-5 brutal-shadow">
          <div className="flex flex-col md:flex-row items-center justify-between gap-5 relative">
            {/* Animated Connector Line */}
            <div className="absolute top-1/2 left-0 right-0 h-2 bg-foreground -translate-y-1/2 hidden md:block z-0"></div>
            <div className="absolute top-0 bottom-0 left-1/2 w-2 bg-foreground -translate-x-1/2 md:hidden z-0"></div>

            {components.slice(0, 3).map((comp, i) => (
              <motion.div 
                key={comp.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.2 }}
                className="bg-surface border-4 border-foreground p-5 z-10 w-full md:w-48 text-center brutal-shadow-sm group hover:-translate-y-2 transition-transform cursor-default"
              >
                <div className="mb-4 flex justify-center">
                   <comp.icon strokeWidth={3} className={`w-10 h-10 ${comp.color} group-hover:scale-110 transition-transform`} />
                </div>
                <h3 className="font-sans font-black uppercase">{comp.name}</h3>
              </motion.div>
            ))}
          </div>

          <div className="h-16 md:h-24 flex items-center justify-center">
             <div className="w-2 h-full bg-foreground relative">
                <div className="absolute inset-0 bg-primary animate-pulse"></div>
             </div>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between gap-5 relative">
            {/* Animated Connector Line */}
            <div className="absolute top-1/2 left-0 right-0 h-2 bg-foreground -translate-y-1/2 hidden md:block z-0"></div>
            <div className="absolute top-0 bottom-0 left-1/2 w-2 bg-foreground -translate-x-1/2 md:hidden z-0"></div>

            {components.slice(3, 6).map((comp, i) => (
              <motion.div 
                key={comp.id}
                initial={{ opacity: 0, y: -20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.2 }}
                className="bg-surface border-4 border-foreground p-5 z-10 w-full md:w-48 text-center brutal-shadow-sm group hover:-translate-y-2 transition-transform cursor-default"
              >
                <div className="mb-4 flex justify-center">
                   <comp.icon strokeWidth={3} className={`w-10 h-10 ${comp.color} group-hover:scale-110 transition-transform`} />
                </div>
                <h3 className="font-sans font-black uppercase">{comp.name}</h3>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
