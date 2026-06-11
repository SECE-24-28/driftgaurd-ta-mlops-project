"use client";

import { motion } from "framer-motion";

export function Solution() {
  const steps = [
    { label: "Deploy Model", desc: "Push your initial model to production.", active: false },
    { label: "Monitor", desc: "DriftGuard tracks live telemetry.", active: false },
    { label: "Detect Drift", desc: "Statistical divergence triggers alert.", active: true },
    { label: "Retrain", desc: "Automated pipeline builds challenger.", active: false },
    { label: "Validate", desc: "Champion vs Challenger evaluation.", active: false },
    { label: "Deploy", desc: "Safe rollout of superior model.", active: false },
    { label: "Govern", desc: "Full audit log of decision history.", active: false },
  ];

  return (
    <section className="py-16 px-4 bg-surface border-b-4 border-foreground overflow-hidden">
      <div className="container mx-auto">
         <div className="text-center mb-6 relative z-10">
          <div className="inline-block bg-accent text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg tracking-wider">
            The Solution
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            DriftGuard Automates the <br/> Entire MLOps Lifecycle
          </h2>
        </div>

        <div className="max-w-2xl mx-auto relative">
          <div className="absolute left-[38px] top-0 bottom-0 w-2 bg-foreground -z-10"></div>
          
          {steps.map((step, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: i * 0.1 }}
              className="flex items-start gap-5 mb-6 relative group"
            >
              <div className={`w-20 h-20 shrink-0 border-4 border-foreground flex items-center justify-center font-sans font-black text-xl transition-colors z-10
                ${step.active ? 'bg-primary text-foreground' : 'bg-background text-foreground group-hover:bg-accent group-hover:text-foreground'} brutal-shadow-sm`}
              >
                {i + 1}
              </div>
              <div className={`flex-1 border-4 border-foreground p-5 brutal-shadow-sm transition-transform
                 ${step.active ? 'bg-primary text-foreground scale-105' : 'bg-background hover:-translate-y-1'}`}
              >
                <h3 className="font-sans font-black text-xl uppercase mb-2">{step.label}</h3>
                <p className={`font-sans font-bold text-lg ${step.active ? 'text-foreground' : 'text-muted-foreground'}`}>{step.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
