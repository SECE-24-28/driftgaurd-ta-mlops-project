"use client";

import { ArrowRight, GitBranch } from "lucide-react";
import Link from "next/link";

export function CTAFooter() {
  return (
    <>
      {/* CTA Section */}
      <section className="py-20 px-4 bg-accent relative overflow-hidden">
         {/* Brutalist Grid overlay */}
         <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'linear-gradient(0deg, transparent 24%, #000 25%, #000 26%, transparent 27%, transparent 74%, #000 75%, #000 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, #000 25%, #000 26%, transparent 27%, transparent 74%, #000 75%, #000 76%, transparent 77%, transparent)', backgroundSize: '40px 40px' }}></div>
         
         <div className="container mx-auto text-center relative z-10">
            <h2 className="text-xl md:text-5xl font-black uppercase tracking-tighter text-background leading-[0.9] mb-6" style={{ textShadow: '4px 4px 0 #111' }}>
              Stop Losing <br/> Accuracy.
            </h2>
            <p className="text-xl md:text-xl font-sans font-black uppercase bg-background text-foreground inline-block px-4 py-2 border-4 border-foreground brutal-shadow mb-6">
              Deploy DriftGuard. Keep your ML production-ready.
            </p>
            
            <div className="flex flex-col sm:flex-row justify-center gap-5">
              <Link href="/dashboard" className="bg-primary text-foreground px-12 py-6 border-4 border-foreground brutal-button flex items-center justify-center gap-2 font-sans font-black text-xl uppercase tracking-wider">
                Start Free <ArrowRight className="w-6 h-6" strokeWidth={4} />
              </Link>
              <Link href="/contact" className="bg-background text-foreground px-12 py-6 border-4 border-foreground brutal-button flex items-center justify-center gap-2 font-sans font-black text-xl uppercase tracking-wider hover:bg-surface">
                Schedule Demo
              </Link>
            </div>
         </div>
      </section>

      {/* Footer Section */}
      <footer className="bg-background border-t-8 border-foreground py-16 px-4">
        <div className="container mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-12 font-sans uppercase font-bold text-sm">
          <div className="col-span-2 lg:col-span-2">
            <div className="flex items-center gap-2 mb-6">
              <div className="bg-primary p-2 border-2 border-foreground">
                <div className="w-4 h-4 bg-background"></div>
              </div>
              <span className="font-black text-xl tracking-tighter">DRIFTGUARD</span>
            </div>
            <p className="text-muted-foreground mb-6 max-w-xs leading-relaxed">
              Automated MLOps platform for drift detection, retraining, and governance.
            </p>
            <div className="flex gap-4">
               <Link href="https://github.com" className="p-3 bg-surface border-2 border-foreground hover:bg-primary hover:text-foreground transition-colors brutal-shadow-sm">
                 <GitBranch className="w-6 h-6" />
               </Link>
            </div>
          </div>

          <div>
            <h4 className="font-black text-lg mb-6 border-b-2 border-foreground pb-2 inline-block">Product</h4>
            <ul className="space-y-4 text-muted-foreground">
              <li><Link href="#" className="hover:text-primary transition-colors">Features</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Integrations</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Pricing</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Changelog</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-black text-lg mb-6 border-b-2 border-foreground pb-2 inline-block">Developers</h4>
            <ul className="space-y-4 text-muted-foreground">
              <li><Link href="#" className="hover:text-primary transition-colors">Documentation</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">API Reference</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Python SDK</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">GitHub</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-black text-lg mb-6 border-b-2 border-foreground pb-2 inline-block">Company</h4>
            <ul className="space-y-4 text-muted-foreground">
              <li><Link href="#" className="hover:text-primary transition-colors">About</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Blog</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Contact</Link></li>
              <li><Link href="#" className="hover:text-primary transition-colors">Security</Link></li>
            </ul>
          </div>
        </div>

        <div className="container mx-auto mt-16 pt-8 border-t-4 border-dashed border-foreground flex flex-col md:flex-row items-center justify-between gap-4 font-sans font-bold text-muted-foreground text-xs uppercase">
          <div>© 2026 DriftGuard Inc. All rights reserved.</div>
          <div className="flex gap-5">
            <Link href="#" className="hover:text-primary">Privacy Policy</Link>
            <Link href="#" className="hover:text-primary">Terms of Service</Link>
          </div>
        </div>
      </footer>
    </>
  );
}
