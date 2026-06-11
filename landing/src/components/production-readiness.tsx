"use client";

import { motion } from "framer-motion";

export function ProductionReadiness() {
  const metrics = [
    { value: "31+", label: "Passing Tests", highlight: "bg-green-500 text-foreground" },
    { value: "100%", label: "Automated Retraining", highlight: "bg-primary text-foreground" },
    { value: "Full", label: "Model Governance", highlight: "bg-surface text-foreground" },
    { value: "<50ms", label: "Drift Detection Latency", highlight: "bg-accent text-foreground" },
    { value: "Strict", label: "Audit Trails", highlight: "bg-surface text-foreground" },
    { value: "Ready", label: "Cloud Deployment", highlight: "bg-secondary text-foreground" },
  ];

  return (
    <section className="py-16 px-4 bg-background border-b-4 border-foreground">
      <div className="container mx-auto">
        <div className="text-center mb-6">
          <div className="inline-block bg-green-500 text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg">
            Enterprise Grade
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            Production Ready. No Excuses.
          </h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-5 max-w-5xl mx-auto">
          {metrics.map((metric, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="border-4 border-foreground bg-background p-5 text-center brutal-shadow hover:-translate-y-2 transition-transform flex flex-col items-center justify-center aspect-square"
            >
              <div className={`font-sans font-black text-4xl md:text-5xl mb-4 px-4 py-2 border-4 border-foreground brutal-shadow-sm ${metric.highlight}`}>
                {metric.value}
              </div>
              <div className="font-sans font-bold uppercase text-lg md:text-xl">
                {metric.label}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
