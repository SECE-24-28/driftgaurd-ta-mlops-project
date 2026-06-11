"use client";

import { motion } from "framer-motion";
import { Landmark, HeartPulse, ShoppingCart, Video, Cpu, ShieldAlert } from "lucide-react";

export function UseCases() {
  const cases = [
    { title: "Banking Fraud Detection", desc: "Detect shifting fraud patterns before they impact the bottom line. Auto-retrain on new adversarial vectors.", icon: Landmark, color: "bg-primary text-foreground" },
    { title: "Healthcare Diagnostics", desc: "Maintain strict compliance while ensuring diagnostic models don't degrade across different demographics.", icon: HeartPulse, color: "bg-accent text-foreground" },
    { title: "Demand Forecasting", desc: "Adapt instantly to supply chain shocks and seasonal anomalies with real-time challenger evaluation.", icon: ShoppingCart, color: "bg-secondary text-foreground" },
    { title: "Recommendation Engines", desc: "Keep user engagement high by automatically retraining when click-through rates start to decay.", icon: Video, color: "bg-red-500 text-foreground" },
    { title: "Manufacturing Analytics", desc: "Monitor predictive maintenance models across thousands of IoT sensors and edge devices.", icon: Cpu, color: "bg-amber-500 text-foreground" },
    { title: "Cybersecurity Systems", desc: "Stay ahead of zero-day threats by continuously validating intrusion detection models.", icon: ShieldAlert, color: "bg-green-500 text-foreground" },
  ];

  return (
    <section className="py-16 px-4 bg-surface border-b-4 border-foreground">
      <div className="container mx-auto">
        <div className="text-center mb-6">
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter bg-foreground text-background inline-block px-6 py-2 border-4 border-foreground brutal-shadow">
            Built for Critical Systems
          </h2>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {cases.map((useCase, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="bg-background border-4 border-foreground brutal-shadow hover:translate-y-2 hover:translate-x-2 hover:shadow-none transition-all duration-200 flex flex-col"
            >
               <div className={`p-4 border-b-4 border-foreground flex items-center justify-between ${useCase.color}`}>
                  <h3 className="font-sans font-black uppercase text-xl leading-tight w-2/3">{useCase.title}</h3>
                  <div className="w-16 h-16 bg-background border-4 border-foreground flex items-center justify-center -mt-8 -mr-8 brutal-shadow-sm">
                     <useCase.icon className="w-6 h-6 text-foreground" strokeWidth={3} />
                  </div>
               </div>
               <div className="p-5 flex-1 bg-background font-sans font-bold text-muted-foreground text-lg">
                  {useCase.desc}
               </div>
               <div className="p-4 border-t-4 border-foreground bg-surface text-center font-sans font-black uppercase text-sm hover:bg-foreground hover:text-foreground transition-colors cursor-pointer">
                  Explore Case Study &rarr;
               </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
