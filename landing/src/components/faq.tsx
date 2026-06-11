"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Minus } from "lucide-react";

export function FAQ() {
  const faqs = [
    {
      q: "How does DriftGuard detect data drift?",
      a: "We use a combination of statistical tests (Kolmogorov-Smirnov, Population Stability Index) and machine learning-based approaches to detect when production feature distributions diverge from training baselines."
    },
    {
      q: "Does it work with any ML framework?",
      a: "Yes. DriftGuard is framework-agnostic. Whether you use Scikit-Learn, TensorFlow, PyTorch, or XGBoost, our Python SDK wraps your inference endpoint seamlessly."
    },
    {
      q: "How is the automated retraining triggered?",
      a: "When drift exceeds your configured threshold, DriftGuard fires a webhook to your CI/CD or ML pipeline (e.g., GitHub Actions, Airflow, MLflow) with the necessary context to kick off a new job."
    },
    {
      q: "Can I self-host DriftGuard?",
      a: "Yes. For enterprise customers, we offer a Docker/Kubernetes deployment model so your data never leaves your VPC."
    },
    {
      q: "What is Champion vs Challenger validation?",
      a: "Before deploying a newly retrained model, DriftGuard routes a shadow copy of live traffic to it (Challenger) and compares its performance against the current model (Champion). It only promotes the Challenger if it proves superior."
    }
  ];

  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-16 px-4 bg-primary/20 border-b-4 border-foreground">
      <div className="container mx-auto max-w-3xl">
        <div className="text-center mb-6">
          <div className="inline-block bg-background text-foreground font-sans font-black px-4 py-1 border-4 border-foreground brutal-shadow-sm mb-4 uppercase text-lg">
            Got Questions?
          </div>
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            FAQ
          </h2>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <div key={i} className="border-4 border-foreground bg-background brutal-shadow-sm overflow-hidden">
              <button
                className={`w-full p-5 text-left flex items-center justify-between font-sans font-black uppercase text-xl transition-colors ${openIndex === i ? 'bg-primary text-foreground' : 'hover:bg-surface'}`}
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
              >
                <span className="pr-8">{faq.q}</span>
                <span className={`p-2 border-2 ${openIndex === i ? 'border-background' : 'border-foreground'} shrink-0`}>
                  {openIndex === i ? <Minus className="w-6 h-6" strokeWidth={3} /> : <Plus className="w-6 h-6" strokeWidth={3} />}
                </span>
              </button>
              
              <AnimatePresence>
                {openIndex === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden bg-surface"
                  >
                    <div className="p-5 font-sans font-bold text-lg text-foreground border-t-4 border-foreground border-dashed">
                      {faq.a}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
