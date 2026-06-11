"use client";

import { Building2, ShoppingCart, HeartPulse, ShieldAlert, Cpu, Landmark } from "lucide-react";

export function TrustedBy() {
  const industries = [
    { name: "FinTech", icon: Landmark },
    { name: "Healthcare", icon: HeartPulse },
    { name: "Retail", icon: ShoppingCart },
    { name: "Manufacturing", icon: Cpu },
    { name: "CyberSec", icon: ShieldAlert },
    { name: "E-Commerce", icon: Building2 },
  ];

  return (
    <section className="py-12 border-y-4 border-foreground bg-primary overflow-hidden flex flex-col items-center relative">
      {/* Brutalist diagonal stripes background */}
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'repeating-linear-gradient(45deg, #000 25%, transparent 25%, transparent 75%, #000 75%, #000), repeating-linear-gradient(45deg, #000 25%, transparent 25%, transparent 75%, #000 75%, #000)', backgroundPosition: '0 0, 10px 10px', backgroundSize: '20px 20px' }}></div>
      
      <div className="font-sans font-black uppercase tracking-widest text-foreground mb-6 text-center px-4 relative z-10 text-xl border-b-4 border-background pb-2">
        Trusted by teams across industries. Works with any ML model.
      </div>
      
      <div className="w-full inline-flex flex-nowrap overflow-hidden [mask-image:_linear-gradient(to_right,transparent_0,_black_128px,_black_calc(100%-128px),transparent_100%)] relative z-10">
        <ul className="flex items-center justify-center md:justify-start [&_li]:mx-4 [&_img]:max-w-none animate-marquee">
          {industries.map((ind, i) => (
            <li key={i} className="flex items-center gap-3 font-black text-xl uppercase bg-background text-foreground border-4 border-foreground px-6 py-3 brutal-shadow whitespace-nowrap hover:bg-accent transition-colors">
              <ind.icon className="w-6 h-6 text-primary group-hover:text-foreground" strokeWidth={3} />
              {ind.name}
            </li>
          ))}
        </ul>
        <ul className="flex items-center justify-center md:justify-start [&_li]:mx-4 [&_img]:max-w-none animate-marquee" aria-hidden="true">
          {industries.map((ind, i) => (
             <li key={i} className="flex items-center gap-3 font-black text-xl uppercase bg-background text-foreground border-4 border-foreground px-6 py-3 brutal-shadow whitespace-nowrap hover:bg-accent transition-colors">
              <ind.icon className="w-6 h-6 text-primary" strokeWidth={3} />
              {ind.name}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
