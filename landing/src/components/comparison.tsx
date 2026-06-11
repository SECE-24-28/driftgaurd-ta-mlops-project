"use client";

import { Check, X } from "lucide-react";

export function Comparison() {
  const features = [
    { name: "Drift Detection", dg: true, trad: "Partial" },
    { name: "Auto Retraining", dg: true, trad: false },
    { name: "Champion vs Challenger", dg: true, trad: false },
    { name: "Model Versioning", dg: true, trad: true },
    { name: "One-Click Rollback", dg: true, trad: false },
    { name: "Governance Audit Logs", dg: true, trad: "Partial" },
    { name: "Python SDK", dg: true, trad: "Partial" },
    { name: "Automated Deployment", dg: true, trad: false },
  ];

  return (
    <section className="py-16 px-4 bg-primary/10 border-b-4 border-foreground">
      <div className="container mx-auto max-w-5xl">
        <div className="text-center mb-6">
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter bg-background text-foreground inline-block px-4 py-2 border-4 border-foreground brutal-shadow">
            DriftGuard vs The Rest
          </h2>
        </div>

        <div className="overflow-x-auto bg-surface border-4 border-foreground brutal-shadow">
          <table className="w-full text-left font-sans border-collapse">
            <thead>
              <tr className="bg-background text-foreground text-xl uppercase">
                <th className="p-5 border-b-4 border-r-4 border-foreground w-1/3">Feature</th>
                <th className="p-5 border-b-4 border-r-4 border-foreground bg-primary text-foreground w-1/3 text-center">DriftGuard</th>
                <th className="p-5 border-b-4 border-foreground text-muted-foreground w-1/3 text-center">Traditional Monitoring</th>
              </tr>
            </thead>
            <tbody>
              {features.map((feature, i) => (
                <tr key={i} className="hover:bg-background/50 transition-colors">
                  <td className="p-5 border-b-4 border-r-4 border-foreground font-bold text-lg">
                    {feature.name}
                  </td>
                  <td className="p-5 border-b-4 border-r-4 border-foreground text-center">
                    <div className="flex justify-center items-center">
                      <div className="w-10 h-10 bg-green-500 border-2 border-foreground flex items-center justify-center brutal-shadow-sm">
                        <Check className="w-6 h-6 text-foreground" strokeWidth={4} />
                      </div>
                    </div>
                  </td>
                  <td className="p-5 border-b-4 border-foreground text-center text-muted-foreground font-bold text-lg">
                    {feature.trad === true ? (
                      <div className="flex justify-center items-center">
                        <div className="w-10 h-10 bg-surface border-2 border-foreground flex items-center justify-center text-foreground">
                          <Check className="w-6 h-6" strokeWidth={3} />
                        </div>
                      </div>
                    ) : feature.trad === false ? (
                      <div className="flex justify-center items-center">
                        <div className="w-10 h-10 bg-surface border-2 border-foreground flex items-center justify-center text-red-500">
                          <X className="w-6 h-6" strokeWidth={3} />
                        </div>
                      </div>
                    ) : (
                      feature.trad
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
