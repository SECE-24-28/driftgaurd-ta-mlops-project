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
    <section id="features" className="py-16 px-4 bg-primary/20 border-b-4 border-foreground relative">
      {/* Decorative Grid */}
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(0deg, transparent 24%, #6366F1 25%, #6366F1 26%, transparent 27%, transparent 74%, #6366F1 75%, #6366F1 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, #6366F1 25%, #6366F1 26%, transparent 27%, transparent 74%, #6366F1 75%, #6366F1 76%, transparent 77%, transparent)', backgroundSize: '50px 50px' }}></div>
      
      <div className="container mx-auto relative z-10">
        <div className="mb-6 border-b-8 border-foreground pb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <h2 className="text-3xl md:text-4xl font-black uppercase tracking-tighter leading-none bg-background text-foreground inline-block px-4 py-2 border-4 border-foreground brutal-shadow">
            Powerful Features
          </h2>
          <div className="font-sans font-black text-lg uppercase bg-accent text-foreground px-4 py-2 border-4 border-foreground brutal-shadow">
            EVERYTHING YOU NEED
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: (i % 4) * 0.1 }}
              className="bg-background border-4 border-foreground p-5 brutal-shadow hover:bg-primary group hover:-translate-y-2 transition-all cursor-default"
            >
              <feature.icon className="w-10 h-10 mb-4 text-foreground group-hover:text-foreground" strokeWidth={3} />
              <h3 className="font-sans font-black text-xl uppercase leading-tight group-hover:text-foreground">{feature.title}</h3>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
