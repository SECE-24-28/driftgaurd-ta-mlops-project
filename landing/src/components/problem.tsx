"use client";

import { AlertTriangle, TrendingDown, FileWarning, Clock, UserX, EyeOff } from "lucide-react";
import { motion } from "framer-motion";

export function Problem() {
  const problems = [
    { title: "Accuracy Degradation", stat: "↓ 23% avg loss", icon: TrendingDown, color: "text-red-500" },
    { title: "Revenue Loss", stat: "$4.2M avg impact", icon: AlertTriangle, color: "text-amber-500" },
    { title: "Compliance Risks", stat: "67% fail audits", icon: FileWarning, color: "text-red-500" },
    { title: "Delayed Retraining", stat: "14 days avg delay", icon: Clock, color: "text-amber-500" },
    { title: "Manual Monitoring", stat: "120+ hrs/mo wasted", icon: UserX, color: "text-red-500" },
    { title: "Lack of Visibility", stat: "84% have no dashboard", icon: EyeOff, color: "text-amber-500" },
  ];

  return (
    <section id="problem" className="py-16 px-4 bg-background border-b-4 border-foreground">
      <div className="container mx-auto">
        <div className="text-center mb-6">
          <div className="inline-block bg-red-500 text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg tracking-wider">
            The Danger Zone
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            The Hidden Cost of <span className="text-red-500 glitch-text inline-block" data-text="Model Drift">Model Drift</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {problems.map((problem, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="bg-surface border-4 border-foreground p-5 brutal-shadow hover:-translate-y-2 transition-transform"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className={`p-3 border-4 border-foreground bg-background ${problem.color}`}>
                  <problem.icon strokeWidth={3} className="w-6 h-6" />
                </div>
                <h3 className="font-sans font-black text-xl uppercase leading-tight">{problem.title}</h3>
              </div>
              <div className="mt-4 pt-4 border-t-4 border-dashed border-foreground">
                <div className="font-sans font-black text-xl uppercase tracking-wider">{problem.stat}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
