"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Quote } from "lucide-react";

export function Testimonials() {
  const testimonials = [
    {
      quote: "Before DriftGuard, we didn't know our credit scoring model was degrading until customers complained. Now, it's caught and retrained automatically.",
      author: "Sarah Jenkins",
      role: "VP of Data Science",
      company: "FinBank Global",
      color: "bg-primary"
    },
    {
      quote: "The one-click rollback feature saved us during a Black Friday deploy. The challenger model failed under extreme load, and DriftGuard reverted it in seconds.",
      author: "Marcus Chen",
      role: "Lead MLOps Engineer",
      company: "Retail Giant",
      color: "bg-accent"
    },
    {
      quote: "Auditors love the governance logs. Every time a model is retrained, we have a cryptographic trail of why, how, and what the validation scores were.",
      author: "Dr. Elena Rostova",
      role: "Chief AI Officer",
      company: "HealthAI Diagnostics",
      color: "bg-secondary"
    }
  ];

  const [currentIndex, setCurrentIndex] = useState(0);

  const next = () => setCurrentIndex((prev) => (prev + 1) % testimonials.length);
  const prev = () => setCurrentIndex((prev) => (prev - 1 + testimonials.length) % testimonials.length);

  return (
    <section className="py-16 px-4 bg-background border-b-4 border-foreground overflow-hidden">
      <div className="container mx-auto max-w-4xl relative">
        <div className="absolute -top-12 -left-12 opacity-20 hidden md:block">
           <Quote className="w-48 h-48 text-primary" strokeWidth={1} />
        </div>

        <div className="text-center mb-6 relative z-10">
          <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter">
            Don't Just Take <span className="text-accent glitch-text inline-block" data-text="Our Word">Our Word</span>
          </h2>
        </div>

        <div className="relative border-4 border-foreground brutal-shadow bg-surface min-h-[400px] flex items-center justify-center p-5 md:p-16">
           <AnimatePresence mode="wait">
             <motion.div
               key={currentIndex}
               initial={{ opacity: 0, x: 50 }}
               animate={{ opacity: 1, x: 0 }}
               exit={{ opacity: 0, x: -50 }}
               transition={{ duration: 0.3 }}
               className="text-center"
             >
                <p className="font-sans font-black text-xl md:text-3xl uppercase leading-tight mb-6">
                  "{testimonials[currentIndex].quote}"
                </p>
                <div className="inline-block p-4 border-4 border-foreground bg-background brutal-shadow-sm">
                   <div className="font-black text-xl uppercase mb-1">{testimonials[currentIndex].author}</div>
                   <div className="font-sans font-bold text-muted-foreground uppercase text-sm">
                     {testimonials[currentIndex].role} @ {testimonials[currentIndex].company}
                   </div>
                </div>
             </motion.div>
           </AnimatePresence>

           <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 flex gap-4">
              <button 
                onClick={prev}
                className={`w-10 h-10 flex items-center justify-center border-4 border-foreground ${testimonials[currentIndex].color} text-foreground brutal-button hover:scale-110 transition-transform`}
              >
                <ChevronLeft className="w-6 h-6" strokeWidth={3} />
              </button>
              <button 
                onClick={next}
                className={`w-10 h-10 flex items-center justify-center border-4 border-foreground ${testimonials[currentIndex].color} text-foreground brutal-button hover:scale-110 transition-transform`}
              >
                <ChevronRight className="w-6 h-6" strokeWidth={3} />
              </button>
           </div>
        </div>
      </div>
    </section>
  );
}
