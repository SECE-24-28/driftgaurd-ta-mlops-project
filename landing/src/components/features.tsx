"use client";

import { motion } from "framer-motion";
import { 
  ActivitySquare, RotateCw, GitCompare, History, 
  Undo2, FileText, BarChart3, BellRing, 
  Box, LayoutDashboard, Code2, Cloud 
} from "lucide-react";

export function Features() {
  const features = [
    { title: "Real-Time Drift Detection", icon: ActivitySquare },
    { title: "Automated Retraining", icon: RotateCw },
    { title: "Champion vs Challenger", icon: GitCompare },
    { title: "Model Versioning", icon: History },
    { title: "One-Click Rollback", icon: Undo2 },
    { title: "Governance & Audit Logs", icon: FileText },
    { title: "Prediction Telemetry", icon: BarChart3 },
    { title: "Alerting System", icon: BellRing },
    { title: "MLflow Integration", icon: Box },
    { title: "Production Dashboard", icon: LayoutDashboard },
    { title: "SDK Integration", icon: Code2 },
    { title: "Cloud-Native Deployment", icon: Cloud },
  ];

  return (
    <section id="features" className="py-24 px-4 bg-primary/20 border-b-4 border-foreground relative">
      {/* Decorative Grid */}
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(0deg, transparent 24%, #6366F1 25%, #6366F1 26%, transparent 27%, transparent 74%, #6366F1 75%, #6366F1 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, #6366F1 25%, #6366F1 26%, transparent 27%, transparent 74%, #6366F1 75%, #6366F1 76%, transparent 77%, transparent)', backgroundSize: '50px 50px' }}></div>
      
      <div className="container mx-auto relative z-10">
        <div className="mb-16 border-b-8 border-foreground pb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <h2 className="text-5xl md:text-7xl font-black uppercase tracking-tighter leading-none bg-background text-foreground inline-block px-4 py-2 border-4 border-foreground brutal-shadow">
            Powerful Features
          </h2>
          <div className="font-mono font-black text-xl uppercase bg-accent text-background px-4 py-2 border-4 border-foreground brutal-shadow">
            EVERYTHING YOU NEED
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: (i % 4) * 0.1 }}
              className="bg-background border-4 border-foreground p-6 brutal-shadow hover:bg-primary group hover:-translate-y-2 transition-all cursor-default"
            >
              <feature.icon className="w-12 h-12 mb-4 text-foreground group-hover:text-background" strokeWidth={3} />
              <h3 className="font-mono font-black text-xl uppercase leading-tight group-hover:text-background">{feature.title}</h3>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
